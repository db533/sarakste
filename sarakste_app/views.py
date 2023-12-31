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

    # Create data structure for template
    segment_links = []
    for segment in segments:
        snippet_link = None
        if segment.unvalidated_snippets_count > 0:
            snippet_place = segment.unvalidated_snippet_place
            snippet_link = f"https://sarakste.digitalaisbizness.lv/lasit/?edit=True&frag1={segment.id}&place1={snippet_place}"
        # Prepare url to view all segment.
        snippets = Snippet.objects.filter(segment=segment).order_by('place')[:2]
        length = segment.length
        if snippets.exists():
            url = "https://sarakste.digitalaisbizness.lv/lasit/?edit=True&frag1={}&place1={}".format(segment.id,
                                                                                                     snippets[0].place)
            if snippets.count() > 1:
                url += "&frag2={}&place2={}".format(segment.id, snippets[1].place)

        segment_links.append({
            'segment_id': segment.id,
            'validated_snippets_count': segment.validated_snippets_count,
            'unvalidated_snippets_count': segment.unvalidated_snippets_count,
            'snippet_link': snippet_link,
            'segment_link' : url
        })

    # Pass the data to the template
    context = {'segment_links': segment_links}
    return render(request, 'segment_list.html', context)

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


def validate_segment_and_snippets(validated_segment, position):
    print('Segment',position,'validated:', validated_segment.id, flush=True)
    validated_segment.validated = True
    validated_segment.save()
    validated_snippets = Snippet.objects.filter(segment=validated_segment)
    for validated_snippet in validated_snippets:
        validated_snippet.validated = True
        validated_snippet.save()

@login_required
def display_snippets(request):

    # Get all segments
    segment_ids = Segment.objects.order_by('id').values_list('id', flat=True)
    # Convert the QuerySet to a list (optional, as QuerySets are iterable)
    segment_ids_list = list(segment_ids)
    print(segment_ids_list)

    if segment_ids:
        max_segment = segment_ids_list[-1]
        min_segment = segment_ids_list[0]
    else:
        max_segment = None  # or some default value, or handle the empty list case as needed
        min_segment = None  # or some default value, or handle the empty list case as needed
    # Initialize variable
    search_left = None
    # Check if we have the data in the session
    search_dict_left = request.session.get('search_dict_left', None)
    search_phrase_left = request.session.get('search_phrase_left', '')
    search_dict_right = request.session.get('search_dict_right', None)
    search_phrase_right = request.session.get('search_phrase_right', '')
    print('Data retrieved from session:')
    print('search_phrase_left:',search_phrase_left, 'search_phrase_right:',search_phrase_right,'search_dict_left:',search_dict_left, 'search_dict_right:',search_dict_right)

    if search_dict_left:
        # Use the stored data
        #search_dict_left = search_dict_left
        pass
    else:
        # Initialize as None or perform the search as needed
        search_dict_left = None

    if search_dict_right:
        # Use the stored data
        #search_snippets_right = snippets_dict_right
        pass
    else:
        # Initialize as None or perform the search as needed
        search_dict_right = None

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
            search_phrase_left = request.POST.get('search_phrase_left', '').strip()
            print("Search Term - left:", search_phrase_left.encode('utf-8'))
            if search_phrase_left == '':
                if 'search_dict_left' in request.session:
                    del request.session['search_dict_left']
                if 'search_phrase_left' in request.session:
                    del request.session['search_phrase_left']
                search_dict_left = {}
                # Store in session
                request.session['search_dict_left'] = search_dict_left

            if len(search_phrase_left) > 0:
                # We have a search phrase passed for the left image.
                if update_local_database:
                    db_name = env.str('MYSQL_LOCAL_DB_NAME')
                else:
                    db_name = env.str('MYSQL_PROD_DB_NAME')

                sentence_table = db_name + '.sarakste_app_sentence'
                snippet_table = db_name + '.sarakste_app_snippet'
                with connection.cursor() as cursor:
                    sql = f"""
                                      SELECT DISTINCT snippet_id 
                                      FROM {sentence_table}
                                      INNER JOIN {snippet_table}  
                                      ON {sentence_table}.snippet_id = {snippet_table}.id
                                      WHERE MATCH(text) AGAINST (%s IN NATURAL LANGUAGE MODE);
                                      """

                    # SELECT DISTINCT snippet_id
                    # FROM sarakste_local.sarakste_app_sentence
                    # INNER JOIN sarakste_local.sarakste_app_snippet
                    # ON sarakste_local.sarakste_app_sentence.snippet_id = sarakste_local.sarakste_app_snippet.id
                    # WHERE MATCH(text) AGAINST ("Esmu klāt" IN NATURAL LANGUAGE MODE);

                    cursor.execute(sql, [search_phrase_left])
                    snippet_ids = [row[0] for row in cursor.fetchall()]
                    print("Snippet IDs found:", snippet_ids)

                search_snippets_left = Snippet.objects.filter(id__in=snippet_ids)
                print("Snippets found:", search_snippets_left)
                search_dict_left = {snippet.id: {'segment_id': snippet.segment.id, 'place': snippet.place} for snippet in
                                 search_snippets_left}
                # Store in session
                request.session['search_dict_left'] = search_dict_left
                request.session['search_phrase_left'] = search_phrase_left
                request.session.modified = True
                # context['search_phrase_left'] = search_left

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
            search_phrase_right = request.POST.get('search_phrase_right', '').strip()
            print("Search Term - right:", search_phrase_right.encode('utf-8'))
            if search_phrase_right == '':
                if 'search_dict_right' in request.session:
                    del request.session['search_dict_right']
                if 'search_phrase_right' in request.session:
                    del request.session['search_phrase_right']
                search_dict_right = {}
                # Store in session
                request.session['search_dict_right'] = search_dict_right

            if len(search_phrase_right) > 0:
                # We have a search phrase passed for the left image.
                if update_local_database:
                    db_name = env.str('MYSQL_LOCAL_DB_NAME')
                else:
                    db_name = env.str('MYSQL_PROD_DB_NAME')

                sentence_table = db_name + '.sarakste_app_sentence'
                snippet_table = db_name + '.sarakste_app_snippet'
                with connection.cursor() as cursor:
                    sql = f"""
                                      SELECT DISTINCT snippet_id 
                                      FROM {sentence_table}
                                      INNER JOIN {snippet_table}  
                                      ON {sentence_table}.snippet_id = {snippet_table}.id
                                      WHERE MATCH(text) AGAINST (%s IN NATURAL LANGUAGE MODE);
                                      """

                    # SELECT DISTINCT snippet_id
                    # FROM sarakste_local.sarakste_app_sentence
                    # INNER JOIN sarakste_local.sarakste_app_snippet
                    # ON sarakste_local.sarakste_app_sentence.snippet_id = sarakste_local.sarakste_app_snippet.id
                    # WHERE MATCH(text) AGAINST ("Esmu klāt" IN NATURAL LANGUAGE MODE);

                    cursor.execute(sql, [search_phrase_right])
                    snippet_ids = [row[0] for row in cursor.fetchall()]
                    print("Snippet IDs found:", snippet_ids)

                search_snippets_right = Snippet.objects.filter(id__in=snippet_ids)
                print("Snippets found:", search_snippets_right)
                search_dict_right = {snippet.id: {'segment_id': snippet.segment.id, 'place': snippet.place} for snippet in
                                 search_snippets_right}
                # Store in session
                request.session['search_dict_right'] = search_dict_right
                request.session['search_phrase_right'] = search_phrase_right
                request.session.modified = True
                # context['search_phrase_right'] = search_right

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
                Sentence.objects.filter(id=sentence_id).update(text=sentence_text)
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
            new_segment = Segment.objects.create(length=0)
            last_place_left = snippet1.place  # This will be the place value that is last to remain in the orignial segment.
            donatable_snippets = Snippet.objects.filter(segment=snippet1.segment).order_by('place')
            new_place_counter = 1
            for donated_snippet in donatable_snippets:
                if donated_snippet.place > last_place_left:
                    donated_snippet.segment = new_segment
                    donated_snippet.place = new_place_counter
                    donated_snippet.validated = False
                    donated_snippet.save()
                    new_place_counter += 1
            new_segment.length = new_place_counter
            new_segment.save()
            old_segment = snippet1.segment
            old_segment.validated = False
            remaining_snippets = Snippet.objects.filter(segment=old_segment)
            for remaining_snippet in remaining_snippets:
                remaining_snippet.validated = False
                remaining_snippet.save()
            old_segment.length = last_place_left
            old_segment.save()
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
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag1}&place2={place2}&edit={edit_mode}&saved=true')
        if 'validate_1' in request.POST:
            # User has indicated that the snippets in segment on left are in correct sequence.
            validated_segment = snippet1.segment
            validate_segment_and_snippets(validated_segment, 'left')
        if 'validate_2' in request.POST:
            # User has indicated that the snippets in segment on left are in correct sequence.
            validated_segment = snippet2.segment
            validate_segment_and_snippets(validated_segment, 'right')



        if snippet2:
            print('Values before redirect when snippet2 exists:')
            print('search_phrase_left:', search_phrase_left, 'search_phrase_right:', search_phrase_right,
                  'search_dict_left:', search_dict_left, 'search_dict_right:', search_dict_right)
            redirect_link = f'/lasit/?frag1={nav_frag1}&place1={nav_place1}&frag2={nav_frag2}&place2={nav_place2}&edit={edit_mode}&saved=true'
        else:
            print('Values before redirect when snippet2 does not exist:')
            print('search_phrase_left:', search_phrase_left, 'search_phrase_right:', search_phrase_right,
                  'search_dict_left:', search_dict_left, 'search_dict_right:', search_dict_right)
            return redirect(f'/lasit/?frag1={nav_frag1}&place1={nav_place1}&edit={edit_mode}&saved=true')
        #f'/lasit/?frag1={nav_frag1}&place1={nav_place1}&frag2={nav_frag2}&place2={nav_place2}&edit={edit_mode}&saved=true')

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
        if place1 == max_place_segment_1:
            max_place_segment_1 = None
        precisedate1 = snippet1.precisedate

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
        if place2 == max_place_segment_2:
            max_place_segment_2 = None
        precisedate2 = snippet2.precisedate

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

    # Check if snippet1 and 2 are in the same segment and are consequetive place number.
    # Used to determine if they can be marked for splitting.
    if snippet1 is not None and snippet2 is not None:
        show_split_checkbox = (snippet1.segment == snippet2.segment)
        show_split_checkbox = show_split_checkbox and (snippet2.place - snippet1.place == 1)
    else:
        show_split_checkbox = False

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
        'show_validate_1' : is_last_place_snippet1, 'show_validate_2' : is_last_place_snippet2,
        'show_split_checkbox': show_split_checkbox,
        'search_dict_left': search_dict_left, 'search_dict_right': search_dict_right,
        'search_phrase_left': search_phrase_left, 'search_phrase_right': search_phrase_right,
        'precisedate1' : precisedate1, 'precisedate2' : precisedate2,
    }

    #print('Context:',context)
    return render(request, 'snippets_display.html', context)

