from django.shortcuts import render, get_object_or_404
from .models import *
from django.contrib.auth.decorators import login_required
from django.db.models import F, Max, Count, Subquery, OuterRef, Q, Value
from django.db.models.functions import Concat

from .forms import SearchForm
from django.db import connection
from datetime import date

import environ
env = environ.Env()
environ.Env.read_env(overwrite=True)

update_local_database = env.bool('update_local_database', default=False)
HOSTED = env.bool('HOSTED', default=False)

def login_view(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'})


from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def generate_segment_links(request):
    # Subquery to get a single unvalidated snippet place for each segment
    unvalidated_snippet_subquery = Subquery(
        Snippet.objects.filter(segment=OuterRef('pk'), validated=False)
        .order_by('place')[:1]
        .values('place')
    )

    # Annotate segments with counts and unvalidated snippet link
    segments = Segment.objects.annotate(
        validated_snippets_count=Count('snippet', filter=Q(snippet__validated=True)),
        unvalidated_snippets_count=Count('snippet', filter=Q(snippet__validated=False)),
        unvalidated_snippet_place=unvalidated_snippet_subquery
    ).order_by('id')

    # Create two separate lists for the template
    segments_with_unvalidated = []
    segments_all_validated = []
    total_segments_count = Segment.objects.count()
    total_snippets_count = Snippet.objects.count()
    validated_snippet_count = Snippet.objects.filter(validated=1).count()
    percent_validated = int(validated_snippet_count*100/total_snippets_count)

    for segment in segments:
        snippet_link = None
        if segment.unvalidated_snippets_count > 0:
            snippet_place = segment.unvalidated_snippet_place
            if HOSTED == True:
                snippet_link = f"https://sarakste.digitalaisbizness.lv/lasit/?edit=True&frag1={segment.id}&place1={snippet_place}"
            else:
                snippet_link = f"http://127.0.0.1:8000/lasit/?edit=True&frag1={segment.id}&place1={snippet_place}"
        # Prepare url to view all segment.
        snippets = Snippet.objects.filter(segment=segment).order_by('place')[:2]
        length = segment.length
        if snippets.exists():
            if HOSTED == True:
                url = "https://sarakste.digitalaisbizness.lv/lasit/?edit=True&frag1={}&place1={}".format(segment.id,snippets[0].place)
            else:
                url = "http://127.0.0.1:8000/lasit/?edit=True&frag1={}&place1={}".format(segment.id,snippets[0].place)
            if snippets.count() > 1:
                url += "&frag2={}&place2={}".format(segment.id, snippets[1].place)

        # Get the snippet that is pointed to as the prior filename from the 1st place Snippet in the segment.
        try:
            first_snippet = Snippet.objects.get(segment=segment,place=1)
        except:
            first_snippet = None
        if first_snippet is not None and first_snippet.filename_prior is not None:
            prior_filename_snippet = first_snippet.filename_prior
            prior_snippet_overlap, created = SnippetOverlap.objects.get_or_create(first_snippet=prior_filename_snippet,second_snippet=first_snippet)
        else:
            prior_filename_snippet = None
            prior_snippet_overlap = None

        # Get the snippet that is pointed to as the next filename from the last place Snippet in the segment.
        try:
            last_snippet = Snippet.objects.get(segment=segment,place=segment.length)
        except:
            last_snippet = None
        if last_snippet is not None and last_snippet.filename_next is not None:
            next_filename_snippet = last_snippet.filename_next
            next_snippet_overlap, created = SnippetOverlap.objects.get_or_create(first_snippet=last_snippet,second_snippet=next_filename_snippet)
        else:
            next_filename_snippet = None
            next_snippet_overlap = None

        segment_data = {
            'segment_id': segment.id,
            'validated_snippets_count': segment.validated_snippets_count,
            'unvalidated_snippets_count': segment.unvalidated_snippets_count,
            'snippet_link': snippet_link,
            'segment_link': url,
            'first_snippet' : first_snippet,
            'last_snippet' : last_snippet,
            'prior_filename_snippet' : prior_filename_snippet,
            'next_filename_snippet' : next_filename_snippet,
            'prior_snippet_overlap' : prior_snippet_overlap,
            'next_snippet_overlap' : next_snippet_overlap,
        }
        # Segregate the segments into two lists
        if segment.unvalidated_snippets_count > 0:
            segments_with_unvalidated.append(segment_data)
        else:
            segments_all_validated.append(segment_data)

    # Pass the data to the template
    context = {
        'segments_with_unvalidated': segments_with_unvalidated, 'segments_all_validated': segments_all_validated,
        'total_segments_count' : total_segments_count, 'total_snippets_count' : total_snippets_count,
        'validated_snippet_count' : validated_snippet_count, 'percent_validated' : percent_validated}
    return render(request, 'segment_list.html', context)

@login_required
def delete_snippet(request, snippet_id):
    snippet = get_object_or_404(Snippet, id=snippet_id)
    current_segment = snippet.segment
    place_of_deletable_snippet = snippet.place

    # Loop through all snippets with higher place number and reduce by 1.
    higher_snippets = Snippet.objects.filter(segment=current_segment).filter(place__gt=place_of_deletable_snippet)
    for higher_snippet in higher_snippets:
        higher_snippet.place = higher_snippet.place - 1
        higher_snippet.save()

    # Check if this is the last snippet in a segment and delete the segment if it is.
    snippets_in_segment_count = Snippet.objects.filter(segment=current_segment).count()
    if snippets_in_segment_count == 1:
        current_segment.delete()

    snippet.delete()
    # Get the 'next' parameter from the query string
    next_url = request.GET.get('next', '')  # Default to an empty string if 'next' isn't provided
    if next_url:
        return redirect(next_url)
    else:
        # Redirect to a default URL if 'next' parameter is not provided
        return redirect('display_snippets')

@login_required
def list_marked_snippets(request):
    user = request.user
    if not user.is_authenticated:
        # Redirect to login page or show a message if the user is not logged in
        return redirect('login_view')

    marked_snippets = Snippet.objects.filter(usersnippet__user=user, usersnippet__marked=True)

    context = {
        'marked_snippets': marked_snippets
    }

    return render(request, 'marked_loved_list.html', context)

@login_required
def list_loved_snippets(request):
    user = request.user
    if not user.is_authenticated:
        # Redirect to login page or show a message if the user is not logged in
        return redirect('login_view')

    loved_snippets = Snippet.objects.filter(usersnippet__user=user, usersnippet__loved=True)

    context = {
        'loved_snippets': loved_snippets,
    }

    return render(request, 'loved_list.html', context)

@login_required
def display_summaries(request):
    summaries = Summary.objects.all()

    # Create data structure for template
    summary_list = []
    for summary in summaries:
        snippets_in_summary = Snippet.objects.filter(summary=summary)
        snippets_in_summary_count = Snippet.objects.filter(summary=summary).count()
        if snippets_in_summary_count > 0:
            summary_list.append({'summary' : summary,
                                 'snippets_in_summary' : snippets_in_summary,
                                 'snippets_in_summary_count' : snippets_in_summary_count})
    # Pass the data to the template
    context = {'summary_list': summary_list}
    return render(request, 'summary_list.html', context)


@login_required
def search(request):

    # SQL command performed to add Full Text index to text field of Sentence model:
    # ALTER TABLE saknesar_sarakste.sarakste_app_sentence ADD FULLTEXT INDEX idx_fulltext (text);

    form = SearchForm(request.GET or None)
    search_results = []  # Initialize search_results at the start

    if update_local_database:
        db_name = env.str('MYSQL_LOCAL_DB_NAME')
    else:
        db_name = env.str('MYSQL_PROD_DB_NAME')

    sentence_table = db_name + '.sarakste_app_sentence'
    snippet_table = db_name + '.sarakste_app_snippet'
    print('sentence_table:', sentence_table)
    print('snippet_table:', snippet_table)
    query_type = ''

    if request.GET and form.is_valid():  # Check if the form is valid
        query = form.cleaned_data['query']
        query_like = form.cleaned_data['query_like']
        query_like_reply = form.cleaned_data['query_like_reply']
        query_like_filename = form.cleaned_data['query_like_filename']
        query_first_time = form.cleaned_data.get('query_first_time')
        query_last_time = form.cleaned_data.get('query_last_time')

        # Adding logic to decide which results to return.
        if len(query) > 0:

            with connection.cursor() as cursor:
                sql = f"""
                          SELECT DISTINCT sent.id, snip.id, MATCH(sent.text) AGAINST (%s IN NATURAL LANGUAGE MODE) AS relevance_score
                          FROM {sentence_table} sent
                          INNER JOIN {snippet_table} snip ON sent.snippet_id = snip.id
                          WHERE MATCH(sent.text) AGAINST (%s IN NATURAL LANGUAGE MODE)
                          ORDER BY relevance_score DESC;
                          """
                cursor.execute(sql, [query, query])
                results = cursor.fetchall()
            for row in results:
                sentence_id, snippet_id, relevance_score = row
                sentence = Sentence.objects.get(id=sentence_id)
                snippet = Snippet.objects.get(id=snippet_id)
                search_results.append({'sentence': sentence, 'snippet': snippet, 'score': relevance_score})
            query_type = 'full text'
        elif len(query_like) > 0:
            with connection.cursor() as cursor:
                sql = f"""
                          SELECT DISTINCT sent.id, snip.id
                          FROM {sentence_table} sent
                          INNER JOIN {snippet_table} snip ON sent.snippet_id = snip.id
                          WHERE sent.text LIKE %s
                          """
                like_query = f"%{query_like}%"
                cursor.execute(sql, [like_query])
                results = cursor.fetchall()
            query_type = 'like text'
        elif len(query_like_reply) > 0:
            with connection.cursor() as cursor:
                sql = f"""
                          SELECT DISTINCT sent.id, snip.id
                          FROM {sentence_table} sent
                          INNER JOIN {snippet_table} snip ON sent.snippet_id = snip.id
                          WHERE sent.reply_to_text LIKE %s
                          """
                like_query = f"%{query_like_reply}%"
                cursor.execute(sql, [like_query])
                results = cursor.fetchall()
            query_type = 'like reply_to_text'
        elif len(query_like_filename) > 0:
            with connection.cursor() as cursor:
                sql = f"""
                          SELECT DISTINCT snip.id
                          FROM {snippet_table} snip
                          WHERE snip.filename LIKE %s
                          """
                like_query = f"%{query_like_filename}%"
                cursor.execute(sql, [like_query])
                results = cursor.fetchall()
                for snippet_id_tuple in results:
                    snippet_id = snippet_id_tuple[0]  # Extract the ID from the tuple
                    snippet = Snippet.objects.get(id=snippet_id)
                    search_results.append({'snippet': snippet})
            query_type = 'like filename'
        elif query_first_time:
            snippets_with_time = Snippet.objects.filter(first_time=query_first_time)
            for snippet in snippets_with_time:
                # Add these snippets to your search results
                search_results.append({'snippet': snippet})
            query_type = 'first_time match'
        elif query_last_time:
            snippets_with_time = Snippet.objects.filter(last_time=query_last_time)
            for snippet in snippets_with_time:
                # Add these snippets to your search results
                search_results.append({'snippet': snippet})
            query_type = 'last_time match'
        if len(query_like) > 0 or len(query_like_reply) > 0:
            for row in results:
                sentence_id, snippet_id = row
                sentence = Sentence.objects.get(id=sentence_id)
                snippet = Snippet.objects.get(id=snippet_id)
                relevance_score = 1
                search_results.append({'sentence': sentence, 'snippet': snippet, 'score': relevance_score})

        # Ensure search_results is always passed to the template, even if it's empty

    return render(request, 'search.html', {'form': form, 'search_results': search_results, 'query_type' : query_type})


def validate_segment_and_snippets(validated_segment, snippet, position):
    print('Segment', position, 'validated:', validated_segment.id, flush=True)
    last_place = snippet.place
    max_last_place = Snippet.objects.filter(segment=validated_segment).aggregate(Max('place'))['place__max']
    #print('last_place:', last_place, 'max_last_place:', max_last_place, flush=True)
    if last_place == max_last_place:
        validated_segment.validated = True
        validated_segment.save()
    validated_snippets = Snippet.objects.filter(segment=validated_segment)
    for validated_snippet in validated_snippets:
        #print('Checking snippet,',validated_snippet.id,' is place',validated_snippet.place,'<=',last_place)
        if validated_snippet.place <= last_place:
            #print('It is. :)')
            validated_snippet.validated = True
            validated_snippet.save()

def create_new_sentence(snippet, request, new_sentence_speaker, sentence_sequence_field, new_sentence_text_field, reply_to_field, time_field):
    new_sentence_sequence = request.POST.get(sentence_sequence_field)
    try:
        new_sentence_sequence = int(new_sentence_sequence)
    except:
        print('new_sentence_sequence must be defined as an integer')
    max_sequence = Sentence.objects.filter(snippet=snippet).aggregate(Max('sequence'))['sequence__max']
    #print('max_sequence:', max_sequence)
    if new_sentence_sequence <= max_sequence:
        #print('new_sentence_sequence <= max_sequence')
        moved_sentences = Sentence.objects.filter(snippet=snippet).filter(sequence__gte=new_sentence_sequence)
        for moved_sentence in moved_sentences:
            moved_sentence.sequence = moved_sentence.sequence + 1
            moved_sentence.save()
    else:
        #print('Adding sentence as new last sentence.')
        new_sentence_sequence = max_sequence + 1
    #print('new_sentence_sequence:', new_sentence_sequence)
    new_sentence_text = request.POST.get(new_sentence_text_field)
    new_sentence_reply_to_text = request.POST.get(reply_to_field)
    new_sentence_time = request.POST.get(time_field)
    if new_sentence_time != "":
        Sentence.objects.create(snippet=snippet,
                                speaker=int(new_sentence_speaker),
                                text=new_sentence_text,
                                reply_to_text=new_sentence_reply_to_text,
                                time=new_sentence_time,
                                sequence=new_sentence_sequence, )
    else:
        Sentence.objects.create(snippet=snippet,
                                speaker=int(new_sentence_speaker),
                                text=new_sentence_text,
                                reply_to_text=new_sentence_reply_to_text,
                                sequence=new_sentence_sequence, )


def split_segment(current_snippet, split_position):
    print('Splitting segment. split_position:',split_position, flush=True)
    new_segment = Segment.objects.create(length=0)
    print('new_segment:',new_segment, flush=True)
    old_segment = current_snippet.segment
    last_place_left = current_snippet.place  # This will be the place value that is last to remain in the orignial segment.
    if split_position == 'before':
        last_place_left -= 1
    print('last_place_left in original segment:', last_place_left, flush=True)
    donatable_snippets = Snippet.objects.filter(segment=old_segment).order_by('place')
    new_place_counter = 1
    for donated_snippet in donatable_snippets:
        if donated_snippet.place > last_place_left:
            donated_snippet.segment = new_segment
            donated_snippet.place = new_place_counter
            #donated_snippet.validated = False
            donated_snippet.save()
            new_place_counter += 1
    new_segment.length = new_place_counter
    new_segment.save()

    old_segment.validated = False
    remaining_snippets = Snippet.objects.filter(segment=old_segment)
    #for remaining_snippet in remaining_snippets:
    #    remaining_snippet.validated = False
    #    remaining_snippet.save()
    old_segment.length = last_place_left
    old_segment.save()
    return new_segment


@login_required
def display_snippets(request):

    # Get all segments
    segment_ids = Segment.objects.order_by('id').values_list('id', flat=True)
    # Convert the QuerySet to a list (optional, as QuerySets are iterable)
    segment_ids_list = list(segment_ids)
    #print(segment_ids_list)

    if segment_ids:
        max_segment = segment_ids_list[-1]
        min_segment = segment_ids_list[0]
    else:
        max_segment = None  # or some default value, or handle the empty list case as needed
        min_segment = None  # or some default value, or handle the empty list case as needed
    # Initialize variable
    search_left = None

    if request.method == 'POST':
        # Get navigation parameters from the POST request
        nav_frag1 = request.POST.get('nav_frag1', '').strip()
        nav_place1 = request.POST.get('nav_place1', '').strip()
        nav_frag2 = request.POST.get('nav_frag2', '').strip()
        nav_place2 = request.POST.get('nav_place2', '').strip()

        # Check if the navigation parameters are provided and valid
        if nav_frag1.isdigit() and nav_place1.isdigit():
            # Convert navigation parameters to integers
            frag1 = int(nav_frag1)
            place1 = int(nav_place1)
        else:
            # Fallback to default or GET parameters if POST data is not valid
            frag1 = request.GET.get('frag1', min_segment)
            place1 = request.GET.get('place1', 1)
        if nav_frag2.isdigit() and nav_place2.isdigit():
            # Convert navigation parameters to integers
            frag2 = int(nav_frag2)
            place2 = int(nav_place2)
        else:
            # Fallback to default or GET parameters if POST data is not valid
            frag2 = request.GET.get('frag1', min_segment)
            place2 = request.GET.get('place1', 1)
    else:
        # Use GET parameters if not a POST request
        frag1 = request.GET.get('frag1', min_segment)
        place1 = request.GET.get('place1', 1)
        frag2 = request.GET.get('frag2', min_segment)
        place2 = request.GET.get('place2', 1)
    edit_mode = request.GET.get('edit', 'False') == 'True'

    # Fetch all existing summaries
    summaries = Summary.objects.all()
    try:
        snippet1 = Snippet.objects.get(segment_id=frag1, place=place1)
        user_snippet1, _ = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet1)
    except Snippet.DoesNotExist:
        snippet1 = None
        user_snippet1 = None

    try:
        if frag2 != 'None' and place2 != 'None':
            snippet2 = Snippet.objects.get(segment_id=frag2, place=place2)
            user_snippet2, _ = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet2)
        else:
            snippet2 = None
            user_snippet2 = None
    except Snippet.DoesNotExist:
        snippet2 = None
        user_snippet2 = None

    if snippet1 is not None:
        # Split the segment if requested
        #split_before_snippet1 = request.GET.get('split_before_snippet1')
        print('About to check for split params in GET for snippet1...', flush=True)
        if 'split_before_snippet1' in request.GET:
            print('split_before_snippet1 found.', flush=True)
            new_segment = split_segment(snippet1, 'before')
            if frag1 == frag2 and int(place2) == int(place1) + 1:
                return redirect(
                    f'/lasit/?frag1={new_segment.id}&place1=1&frag2={new_segment.id}&place2=2&edit={edit_mode}&saved=true')
            else:
                return redirect(
                    f'/lasit/?frag1={new_segment.id}&place1=1&frag2={frag2}&place2={place2}&edit={edit_mode}&saved=true')
        #split_after_snippet1 = request.GET.get('split_after_snippet1')
        if 'split_after_snippet1' in request.GET:
            print('split_after_snippet1 found.', flush=True)
            #old_segment = snippet1.segment
            #old_segment_length = Snippet.objects.filter(segment=old_segment).aggregate(Max('place'))['place__max']
            #if place1 == old_segment_length:
            #    print('Requested to split after the last place in a segment. Ignore.')
            #else:
            new_segment = split_segment(snippet1, 'after')
            if frag1 == frag2 and int(place2) == int(place1)+1:
                # Snippet 2 was the next snippet in the segment.
                return redirect(
                    f'/lasit/?frag1={frag1}&place1={place1}&frag2={new_segment.id}&place2=1&edit={edit_mode}&saved=true')
            else:
                return redirect(
                    f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag2}&place2={place2}&edit={edit_mode}&saved=true')
    print('snippet2:',snippet2, flush=True)
    if snippet2 is not None:
        # Split the segment if requested
        #split_before_snippet2 = request.GET.get('split_before_snippet2')
        print('About to check for split params in GET for snippet2...', flush=True)
        if 'split_before_snippet2' in request.GET:
            print('split_before_snippet2 found.', flush=True)
            new_segment = split_segment(snippet2, 'before')
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={new_segment.id}&place2=1&edit={edit_mode}&saved=true')
        #split_after_snippet2 = request.GET.get('split_after_snippet2')
        if 'split_after_snippet2' in request.GET:
            print('split_after_snippet2 found.', flush=True)
            new_segment = split_segment(snippet2, 'after')
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag2}&place2={place2}&edit={edit_mode}&saved=true')
    #if 'split_before_snippet2' in request.GET:
        # User has indicated that these 2 snippets are not in sequence and the segment should eb split into 2 segments.
    #    print('split_before_snippet2 found regardless of snippet2 state.', flush=True)
        # Create a new segment.
    #    new_segment = split_segment(snippet1, 'before')
    #    return redirect(
    #        f'/lasit/?frag1={frag1}&place1={place1}&frag2={new_segment.id}&place2=1&edit={edit_mode}&saved=true')

    if request.method == 'POST':
        context={}
        if snippet1 is not None:
            snippet1.text = request.POST.get('text1', '')
            selected_summary1_id = request.POST.get('selected_summary1')
            new_summary1_title = request.POST.get('new_summary1', '').strip()
            if new_summary1_title:
                new_summary1, _ = Summary.objects.get_or_create(title=new_summary1_title)
                snippet1.summary = new_summary1
            elif selected_summary1_id:
                selected_summary1 = Summary.objects.get(id=selected_summary1_id)
                snippet1.summary = selected_summary1
            precisedate1 = request.POST.get('precisedate1')
            print('precisedate1 from POST:', precisedate1, flush=True)
            if precisedate1 != "":
                snippet1.precisedate = date.fromisoformat(precisedate1)
            snippet1.save()
            new_sentence_speaker = request.POST.get('new_sentence_speaker_1', '')
            print('new_sentence_speaker:',new_sentence_speaker)
            if new_sentence_speaker == "0" or new_sentence_speaker == "1":
                create_new_sentence(snippet1, request, new_sentence_speaker, 'new_sentence_sequence_1', 'new_sentence_text_1', 'new_sentence_reply_to_text_1', 'new_sentence_time_1')


        if snippet2 is not None:
            snippet2.text = request.POST.get('text2', '')
            selected_summary2_id = request.POST.get('selected_summary2')
            new_summary2_title = request.POST.get('new_summary2', '').strip()
            if new_summary2_title:
                new_summary2, _ = Summary.objects.get_or_create(title=new_summary2_title)
                snippet2.summary = new_summary2
            elif selected_summary2_id:
                selected_summary2 = Summary.objects.get(id=selected_summary2_id)
                snippet2.summary = selected_summary2
            precisedate2 =  request.POST.get('precisedate2')
            print('precisedate2 from POST:',precisedate2)
            if precisedate2 != "":
                snippet2.precisedate = date.fromisoformat(precisedate2)
            snippet2.save()
            new_sentence_speaker = request.POST.get('new_sentence_speaker_2', '')
            print('new_sentence_speaker:',new_sentence_speaker)
            if new_sentence_speaker == "0" or new_sentence_speaker == "1":
                create_new_sentence(snippet2, request, new_sentence_speaker, 'new_sentence_sequence_2', 'new_sentence_text_2', 'new_sentence_reply_to_text_2', 'new_sentence_time_2')
        if user_snippet1 is not None:
            user_snippet1.loved = 'loved1' in request.POST
            user_snippet1.marked = 'marked1' in request.POST
            user_snippet1.save()

        if user_snippet2 is not None:
            user_snippet2.loved = 'loved2' in request.POST
            user_snippet2.marked = 'marked2' in request.POST
            user_snippet2.save()

        # Look for modifications to Sentences and update the Sentence instances.
        for key, value in request.POST.items():
            if key.startswith('sentence_id_'):
                sentence_id = value
                sentence_text = request.POST.get(f'sentence_text_{sentence_id}', '').strip()
                sentence_reply = request.POST.get(f'sentence_reply_{sentence_id}', '').strip()
                Sentence.objects.filter(id=sentence_id).update(text=sentence_text)
                Sentence.objects.filter(id=sentence_id).update(reply_to_text=sentence_reply)
            if key.startswith('delete_sentence_'):
                sentence_id = key.split('_')[-1]
                try:
                    sentence_to_delete = Sentence.objects.get(id=sentence_id)
                    sentence_to_delete.delete()
                except Sentence.DoesNotExist:
                    pass  # Handle the case where the sentence does not exist

        # Extract the navigation parameters from the form
        nav_frag1 = request.POST.get('nav_frag1', frag1).strip() or frag1
        nav_place1 = request.POST.get('nav_place1', place1).strip() or place1
        nav_frag2 = request.POST.get('nav_frag2', frag2).strip() or frag2
        nav_place2 = request.POST.get('nav_place2', place2).strip() or place2

        # Redirect to the same page to display updated content
        #return redirect('display_snippets')
        if snippet1 is not None:
            snippet1.save()
        if snippet2 is not None:
            snippet2.save()

        if 'split' in request.POST:
            # User has indicated that these 2 snippets are not in sequence and the segment should eb split into 2 segments.
            # Create a new segment.
            #new_segment = split_segment(snippet1, 'before')
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={new_segment.id}&place2=1&edit={edit_mode}&saved=true')

        if 'combine' in request.POST:
            # User has indicated that these segments need to be combined.
            # Get the segment of the 2nd snippet.
            donating_segment = snippet2.segment
            receiving_segment = snippet1.segment
            receiving_segment.validated = False
            receiving_segment_max_place = Snippet.objects.filter(segment_id=receiving_segment).aggregate(Max('place'))['place__max']

            # Retrieve the snippets that are linked to the Segment in ascending place order.
            donatable_snippets = Snippet.objects.filter(segment=donating_segment) .order_by('place')
            # Change the segment to 1st snippet's segment and adjust the place to be after the final image.
            for donated_snippet in donatable_snippets:
                donated_snippet.segment = receiving_segment
                donated_snippet.place = donated_snippet.place + receiving_segment_max_place
                donated_snippet.save()
                receiving_segment.length += 1
            receiving_segment.save()
            donating_segment.delete()
            place2 = int(place1) + 1
            overlap, created = SnippetOverlap.objects.get_or_create(first_snippet=snippet1, second_snippet=snippet2)
            overlap.checked=True
            overlap.save()
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag1}&place2={place2}&edit={edit_mode}&saved=true')
        if 'validate_1' in request.POST:
            # User has indicated that the snippets from place 1 to current place in segment on left are in correct sequence.
            validated_segment = snippet1.segment
            validate_segment_and_snippets(validated_segment, snippet1, 'left')
        if 'validate_2' in request.POST:
            # User has indicated that the snippets from place 1 to current place in segment on right are in correct sequence.
            validated_segment = snippet2.segment
            validate_segment_and_snippets(validated_segment, snippet2, 'right')
        if 'this_overlap_checked' in request.POST:
            overlap = SnippetOverlap.objects.get(first_snippet=snippet1, second_snippet=snippet2)
            overlap.checked=True
            overlap.save()

    # Determine Previous and Next buttons for each snippet.
    display_next1 = False
    display_prev1 = False
    display_next2 = False
    display_prev2 = False
    display_scroll_left = False
    display_scroll_right = False
    prev_frag1 = 0
    prev_place1 = 0
    next_frag1 = 0
    next_place1 = 0
    prev_frag2 = 0
    prev_place2 = 0
    next_frag2 = 0
    next_place2 = 0
    prior_segment_frag2 = None
    prior_segment_place2 = None
    next_segment_frag2 = None
    next_segment_place2 = None
    prior_segment_frag1 = None
    prior_segment_place1 = None
    next_segment_frag1 = None
    next_segment_place1 = None
    max_place_segment_1 = None
    max_place_segment_2 = None
    precisedate1 = None
    precisedate2 = None
    display_split_before_1 = False
    display_split_before_2 = False
    display_split_after_1 = False
    display_split_after_2 = False

    if snippet1 is not None:
        # Previous button logic
        prev_frag1, prev_place1 = frag1, int(place1) - 1
        display_prev1 = True
        current_frag_index = segment_ids_list.index(int(frag1))
        if prev_place1 < 1:
            # Find the location of this segment in the segment_ids list.
            #current_frag_index = segment_ids_list.index(int(frag1))
            print('snippet1 current_frag_index:',current_frag_index)
            if current_frag_index > 0:
                # This is not the first segment.
                prev_frag1 = segment_ids_list[current_frag_index-1]
                prev_place1 = Snippet.objects.filter(segment=prev_frag1).aggregate(Max('place'))['place__max']
            else:
                display_prev1 = False

        max_place_segment_1 = Snippet.objects.filter(segment=frag1).aggregate(Max('place'))['place__max']
        # Next button logic
        next_frag1, next_place1 = frag1, int(place1) + 1
        display_next1 = True
        if next_place1 > max_place_segment_1:
            # Find the location of this segment in the segment_ids list.
            #current_frag_index = segment_ids_list.index(int(frag1))
            if current_frag_index < len(segment_ids_list)-1:
                # This is not the last segment.
                next_frag1 = segment_ids_list[current_frag_index + 1]
                next_place1 = 1
            else:
                # We were already at the first segment.
                display_next1 = False
        # If this is not the first segment, then include a prior_segment link for snippet2.
        if current_frag_index > 0:
            prior_segment_frag1 = segment_ids_list[current_frag_index - 1]
            prior_segment_place1 = 1
        # If this is not the last segment in the list, then show next_segment link
        if current_frag_index < len(segment_ids_list) - 1:
            next_segment_frag1 = segment_ids_list[current_frag_index + 1]
            next_segment_place1 = 1

        #if place1 == max_place_segment_1:
        #    max_place_segment_1 = None
        precisedate1 = snippet1.precisedate
        if snippet1.place > 1:
            display_split_before_1 = True
        if snippet1.place < max_place_segment_1:
            display_split_after_1 = True

    if snippet2 is not None:
        # Previous button logic
        prev_frag2, prev_place2 = frag2, int(place2) - 1
        display_prev2 = True
        # Find the location of this segment in the segment_ids list.
        current_frag_index = segment_ids_list.index(int(frag2))
        if prev_place2 < 1:
            if current_frag_index > 0:
                # This is not the first segment.
                prev_frag2 = segment_ids_list[current_frag_index-1]
                prev_place2 = Snippet.objects.filter(segment=prev_frag2).aggregate(Max('place'))['place__max']
            else:
                # We were already at the first segment.
                display_prev2 = False
        if display_prev2 == True and display_prev1 == True:
            # We have both 2 snippets and both have prev snippets, so can display a scroll left link.
            display_scroll_left = True

        max_place_segment_2 = Snippet.objects.filter(segment=frag2).aggregate(Max('place'))['place__max']
            # Next button logic
        next_frag2, next_place2 = frag2, int(place2) + 1
        display_next2 = True
        if next_place2 > max_place_segment_2:
            if current_frag_index < len(segment_ids_list)-1:
                # This is not the last segment.
                next_frag2 = segment_ids_list[current_frag_index + 1]
                next_place2 = 1
            else:
                # We were already at the first segment.
                display_next2 = False
        if display_next2 == True and display_next1 == True:
            # We have both 2 snippets and both have next snippets, so can display a scroll right link.
            display_scroll_right = True
        # If this is not the first segment, then include a prior_segment link for snippet2.
        if current_frag_index > 0:
            prior_segment_frag2 = segment_ids_list[current_frag_index - 1]
            prior_segment_place2 = 1
        # If this is not the last segment in the list, then show next_segment link
        if current_frag_index < len(segment_ids_list) - 1:
            next_segment_frag2 = segment_ids_list[current_frag_index + 1]
            next_segment_place2 = 1
        #if place2 == max_place_segment_2:
        #    max_place_segment_2 = None
        precisedate2 = snippet2.precisedate
        if snippet2.place > 1:
            display_split_before_2 = True
        if snippet2.place < max_place_segment_2:
            display_split_after_2 = True
    if snippet1:
        sentences1 = Sentence.objects.filter(snippet=snippet1).order_by('sequence')
        top_ssim_overlaps_as_first_snippet1 = SnippetOverlap.objects.filter(second_snippet=snippet1).order_by(
            '-ssim_score')[:5]
        top_ssim_overlaps_as_second_snippet1 = SnippetOverlap.objects.filter(first_snippet=snippet1).order_by(
            '-ssim_score')[:5]
        top_time_overlaps_as_first_snippet1 = SnippetOverlap.objects.filter(second_snippet=snippet1).order_by(
            'time_diff')[:5]
        top_time_overlaps_as_second_snippet1 = SnippetOverlap.objects.filter(first_snippet=snippet1).order_by(
            'time_diff')[:5]
    else:
        sentences1 = []
        top_ssim_overlaps_as_first_snippet1 = []
        top_ssim_overlaps_as_second_snippet1 = []
        top_time_overlaps_as_first_snippet1 = []
        top_time_overlaps_as_second_snippet1 = []

    if snippet2:
        sentences2 = Sentence.objects.filter(snippet=snippet2).order_by('sequence')
        top_ssim_overlaps_as_first_snippet2 = SnippetOverlap.objects.filter(second_snippet=snippet2).order_by(
            '-ssim_score')[:5]
        top_ssim_overlaps_as_second_snippet2 = SnippetOverlap.objects.filter(first_snippet=snippet2).order_by(
            '-ssim_score')[:5]
        top_time_overlaps_as_first_snippet2 = SnippetOverlap.objects.filter(second_snippet=snippet2).order_by(
            'time_diff')[:5]
        top_time_overlaps_as_second_snippet2 = SnippetOverlap.objects.filter(first_snippet=snippet2).order_by(
            'time_diff')[:5]
    else:
        sentences2 = []
        top_ssim_overlaps_as_first_snippet2 = []
        top_ssim_overlaps_as_second_snippet2 = []
        top_time_overlaps_as_first_snippet2 = []
        top_time_overlaps_as_second_snippet2 = []

    # Check if snippet1's place is the last in its segment and snippet2's place is 1
    # Check used to detmine if combined field should be displayed.
    is_last_place_snippet1 = Snippet.objects.filter(segment_id=frag1).aggregate(Max('place'))['place__max'] == int(place1)
    is_last_place_snippet2 = Snippet.objects.filter(segment_id=frag2).aggregate(Max('place'))['place__max'] == int(place2)
    if snippet2 is not None:
        is_first_place_snippet2 = int(place2) == 1
    else:
        is_first_place_snippet2 = False

    # Adding code to display links to the marked snippets:
    user_marked_snippets = UserSnippet.objects.filter(user=request.user, marked=True).values_list('snippet', flat=True)
    marked_snippets = Snippet.objects.filter(id__in=user_marked_snippets)
    if snippet1 and snippet2:
        overlap, created  = SnippetOverlap.objects.get_or_create(first_snippet=snippet1, second_snippet=snippet2)
    else:
        overlap = None

    context = {
        'snippet1': snippet1,'snippet2': snippet2,
        'user_snippet1': user_snippet1,'user_snippet2': user_snippet2,
        'edit_mode': edit_mode,  # Add edit mode to context
        'frag1' : frag1, 'place1' : place1,
        'frag2' : frag2, 'place2' : place2,
        'display_next1' : display_next1, 'display_prev1' : display_prev1,
        'display_next2': display_next2, 'display_prev2': display_prev2,
        'display_scroll_right' : display_scroll_right, 'display_scroll_left' : display_scroll_left,
        'prev_frag1': prev_frag1, 'prev_place1': prev_place1,
        'prev_frag2': prev_frag2, 'prev_place2': prev_place2,
        'next_frag1': next_frag1, 'next_place1': next_place1,
        'next_frag2': next_frag2, 'next_place2': next_place2,
        'prior_segment_frag1': prior_segment_frag1, 'prior_segment_place1': prior_segment_place1,
        'next_segment_frag1': next_segment_frag1, 'next_segment_place1': next_segment_place1,
        'prior_segment_frag2': prior_segment_frag2, 'prior_segment_place2': prior_segment_place2,
        'next_segment_frag2': next_segment_frag2, 'next_segment_place2': next_segment_place2,
        'max_place_segment_1' : max_place_segment_1, 'max_place_segment_2' : max_place_segment_2,
        'summaries': summaries,
        'sentences1': sentences1,'sentences2': sentences2,
        'top_ssim_overlaps_as_first_snippet1': top_ssim_overlaps_as_first_snippet1,
        'top_ssim_overlaps_as_second_snippet1': top_ssim_overlaps_as_second_snippet1,
        'top_ssim_overlaps_as_first_snippet2': top_ssim_overlaps_as_first_snippet2,
        'top_ssim_overlaps_as_second_snippet2': top_ssim_overlaps_as_second_snippet2,
        'top_time_overlaps_as_first_snippet1': top_time_overlaps_as_first_snippet1,
        'top_time_overlaps_as_second_snippet1': top_time_overlaps_as_second_snippet1,
        'top_time_overlaps_as_first_snippet2': top_time_overlaps_as_first_snippet2,
        'top_time_overlaps_as_second_snippet2': top_time_overlaps_as_second_snippet2,
        'show_combine_checkbox': is_last_place_snippet1 and is_first_place_snippet2,
        'precisedate1' : precisedate1, 'precisedate2' : precisedate2,
        'marked_snippets' : marked_snippets,
        'display_split_after_1' : display_split_after_1, 'display_split_after_2' : display_split_after_2,
        'display_split_before_1': display_split_before_1, 'display_split_before_2' : display_split_before_2,
        'overlap' : overlap,
    }

    #print('Context:',context)
    return render(request, 'snippets_display.html', context)

