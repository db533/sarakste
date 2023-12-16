from django.shortcuts import render, get_object_or_404
from .models import *
from django.contrib.auth.decorators import login_required
from django.db.models import F, Max, Min

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
    segments = Segment.objects.all()
    segment_links = []
    for segment in segments:
        snippets = Snippet.objects.filter(segment=segment).order_by('place')[:2]
        length = segment.length
        if snippets.exists():
            url = "https://sarakste.digitalaisbizness.lv/lasit/?edit=True&frag1={}&place1={}".format(segment.id,
                                                                                           snippets[0].place)
            if snippets.count() > 1:
                url += "&frag2={}&place2={}".format(segment.id, snippets[1].place)
            segment_links.append((segment.id, url, length))
    return render(request, 'segment_list.html', {'segment_links': segment_links})

@login_required
def display_snippets(request):

    min_segment = Snippet.objects.aggregate(Min('segment'))['segment__min']

    # Extract parameters from the request, using default values if not provided
    frag1 = request.GET.get('frag1', min_segment)
    place1 = request.GET.get('place1', 1)
    frag2 = request.GET.get('frag2')
    place2 = request.GET.get('place2')
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
        snippet2 = Snippet.objects.get(segment_id=frag2, place=place2)
        user_snippet2, _ = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet2)
    except Snippet.DoesNotExist:
        snippet2 = None
        user_snippet2 = None

    if request.method == 'POST':
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
            snippet1.save()

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
            snippet2.save()

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
                    donated_snippet.save()
                    new_place_counter += 1
            new_segment.length = new_place_counter
            new_segment.save()
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={new_segment.id}&place2=1&edit={edit_mode}&saved=true')

        if 'combine' in request.POST:
            # User has indicated that these segments need to be combined.
            # Get the segment of the 2nd snippet.
            donating_segment = snippet2.segment
            receiving_segment = snippet1.segment
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

        return redirect(f'/lasit/?frag1={nav_frag1}&place1={nav_place1}&frag2={nav_frag2}&place2={nav_place2}&edit={edit_mode}&saved=true')

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

    # Determine Previous and Next buttons for each snippet.
    display_next1 = False
    display_prev1 = False
    display_next2 = False
    display_prev2 = False
    prev_frag1 = 0
    prev_place1 = 0
    next_frag1 = 0
    next_place1 = 0
    prev_frag2 = 0
    prev_place2 = 0
    next_frag2 = 0
    next_place2 = 0

    if snippet1 is not None:
        # Previous button logic
        prev_frag1, prev_place1 = frag1, int(place1) - 1
        display_prev1 = True
        if prev_place1 < 1:
            # Find the location of this segment in the segment_ids list.
            current_frag_index = segment_ids_list.index(int(frag1))
            print('snippet1 current_frag_index:',current_frag_index)
            if current_frag_index > 0:
                # This is not the first segment.
                prev_frag1 = segment_ids_list[current_frag_index-1]
            else:
                display_prev1 = False

        max_place_segment_1 = Snippet.objects.filter(segment=frag1).aggregate(Max('place'))['place__max']
        # Next button logic
        next_frag1, next_place1 = frag1, int(place1) + 1
        display_next1 = True
        if next_place1 > max_place_segment_1:
            # Find the location of this segment in the segment_ids list.
            current_frag_index = segment_ids_list.index(int(frag1))
            if current_frag_index < len(segment_ids_list)-1:
                # This is not the last segment.
                next_frag1 = segment_ids_list[current_frag_index + 1]
                next_place1 = 1
            else:
                # We were already at the first segment.
                display_next1 = False

    if snippet2 is not None:
        # Previous button logic
        prev_frag2, prev_place2 = frag2, int(place2) - 1
        display_prev2 = True
        if prev_place2 < 1:
            # Find the location of this segment in the segment_ids list.
            current_frag_index = segment_ids_list.index(int(frag2))
            if current_frag_index > 0:
                # This is not the first segment.
                prev_frag2 = segment_ids_list[current_frag_index-1]
            else:
                # We were already at the first segment.
                display_prev2 = False

        max_place_segment_2 = Snippet.objects.filter(segment=frag2).aggregate(Max('place'))['place__max']
        # Next button logic
        next_frag2, next_place2 = frag2, int(place2) + 1
        display_next2 = True
        if next_place2 > max_place_segment_2:
            # Find the location of this segment in the segment_ids list.
            current_frag_index = segment_ids_list.index(int(frag2))
            if current_frag_index < len(segment_ids_list)-1:
                # This is not the last segment.
                next_frag2 = segment_ids_list[current_frag_index + 1]
                next_place2 = 1
            else:
                # We were already at the first segment.
                display_next2 = False

    if snippet1:
        sentences1 = Sentence.objects.filter(snippet=snippet1).order_by('sequence')
        top_overlaps_as_first_snippet1 = SnippetOverlap.objects.filter(second_snippet=snippet1).order_by(
            '-ssim_score')[:3]
        top_overlaps_as_second_snippet1 = SnippetOverlap.objects.filter(first_snippet=snippet1).order_by(
            '-ssim_score')[:3]
    else:
        sentences1 = []
        top_overlaps_as_first_snippet1 = []
        top_overlaps_as_second_snippet1 = []

    if snippet2:
        sentences2 = Sentence.objects.filter(snippet=snippet2).order_by('sequence')
        top_overlaps_as_first_snippet2 = SnippetOverlap.objects.filter(second_snippet=snippet2).order_by(
            '-ssim_score')[:3]
        top_overlaps_as_second_snippet2 = SnippetOverlap.objects.filter(first_snippet=snippet2).order_by(
            '-ssim_score')[:3]
    else:
        sentences2 = []
        top_overlaps_as_first_snippet2 = []
        top_overlaps_as_second_snippet2 = []

    # Check if snippet1's place is the last in its segment and snippet2's place is 1
    # Check used to detmine if combined field should eb displayed.
    is_last_place_snippet1 = Snippet.objects.filter(segment_id=frag1).aggregate(Max('place'))['place__max'] == int(place1)
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
        'prev_frag1': prev_frag1, 'prev_place1': prev_place1,
        'prev_frag2': prev_frag2, 'prev_place2': prev_place2,
        'next_frag1': next_frag1, 'next_place1': next_place1,
        'next_frag2': next_frag2, 'next_place2': next_place2,
        'summaries': summaries,
        'sentences1': sentences1,'sentences2': sentences2,
        'top_overlaps_as_first_snippet1': top_overlaps_as_first_snippet1,
        'top_overlaps_as_second_snippet1': top_overlaps_as_second_snippet1,
        'top_overlaps_as_first_snippet2': top_overlaps_as_first_snippet2,
        'top_overlaps_as_second_snippet2': top_overlaps_as_second_snippet2,
        'show_combine_checkbox': is_last_place_snippet1 and is_first_place_snippet2,
        'show_split_checkbox': show_split_checkbox,
    }

    return render(request, 'snippets_display.html', context)
