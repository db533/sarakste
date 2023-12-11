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
def display_snippets(request):

    min_segment = Snippet.objects.aggregate(Min('segment'))['segment__min']

    # Extract parameters from the request, using default values if not provided
    frag1 = request.GET.get('frag1', min_segment)
    place1 = request.GET.get('place1', 1)
    frag2 = request.GET.get('frag2', min_segment)
    place2 = request.GET.get('place2', 2)
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
            place2 = place1 + 1
            return redirect(
                f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag1}&place2={place2}&edit={edit_mode}&saved=true')

        return redirect(f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag2}&place2={place2}&edit={edit_mode}&saved=true')

    prev_snippet = Snippet.objects.filter(segment_id=frag1, place=F('place') - 1).first()
    if int(place1) > 1:
        prev_snippet_exists = True
    else:
        prev_snippet_exists = False

    # Logic for previous and next buttons
    max_place = Snippet.objects.aggregate(Max('place'))['place__max']
    max_segment = Snippet.objects.aggregate(Max('segment'))['segment__max']

    # Previous button logic
    prev_frag1, prev_place1 = frag1, int(place1) - 1
    if prev_place1 < 1:
        prev_frag1 = int(frag1)-1
        prev_place1 = Snippet.objects.filter(segment_id=prev_frag1).aggregate(Max('place'))['place__max'] or 1
        if prev_frag1 < 1:
            prev_frag1 = 1

    prev_frag2, prev_place2 = frag2, int(place2) - 1
    if prev_place2 < 1:
        prev_frag2 = int(frag2)-1
        prev_place2 = Snippet.objects.filter(segment_id=prev_frag2).aggregate(Max('place'))['place__max'] or 1
        if prev_frag2 < 1:
            prev_frag2 = 1

    # Next button logic
    next_frag1, next_place1 = frag1, int(place1) + 1
    if max_place is not None:
        if next_place1 > max_place:
            next_frag1 = int(frag1)+1
            next_place1 = 1

    next_frag2, next_place2 = frag2, int(place2) + 1
    if max_place is not None:
        if next_place2 > max_place:
            next_frag2 =int(frag2)+1
            next_place2 = 1

    if snippet1:
        sentences1 = Sentence.objects.filter(snippet=snippet1).order_by('sequence')
    else:
        sentences1 = []

    if snippet2:
        sentences2 = Sentence.objects.filter(snippet=snippet2).order_by('sequence')
    else:
        sentences2 = []

    if snippet1:
        top_overlaps_as_first_snippet1 = SnippetOverlap.objects.filter(second_snippet=snippet1).order_by(
            '-overlaprowcount')[:3]
        top_overlaps_as_second_snippet1 = SnippetOverlap.objects.filter(first_snippet=snippet1).order_by(
            '-overlaprowcount')[:3]
    else:
        top_overlaps_as_first_snippet1 = []
        top_overlaps_as_second_snippet1 = []

    if snippet2:
        top_overlaps_as_first_snippet2 = SnippetOverlap.objects.filter(second_snippet=snippet2).order_by(
            '-overlaprowcount')[:3]
        top_overlaps_as_second_snippet2 = SnippetOverlap.objects.filter(first_snippet=snippet2).order_by(
            '-overlaprowcount')[:3]
    else:
        top_overlaps_as_first_snippet2 = []
        top_overlaps_as_second_snippet2 = []

    # Check if snippet1's place is the last in its segment and snippet2's place is 1
    is_last_place_snippet1 = Snippet.objects.filter(segment_id=frag1).aggregate(Max('place'))['place__max'] == int(
        place1)
    is_first_place_snippet2 = int(place2) == 1

    # Check if snippet1 and 2 are in the same segment and are consequetive place number.
    if snippet1 is not None and snippet2 is not None:
        show_split_checkbox = (snippet1.segment == snippet2.segment)
        show_split_checkbox = show_split_checkbox and (snippet2.place - snippet1.place == 1)
    else:
        show_split_checkbox = False

    context = {
        'snippet1': snippet1,'snippet2': snippet2,
        'user_snippet1': user_snippet1,'user_snippet2': user_snippet2,
        'prev_snippet': prev_snippet,
        'edit_mode': edit_mode,  # Add edit mode to context
        'prev_snippet_exists' : prev_snippet_exists,
        'frag1' : frag1, 'place1' : place1,
        'frag2' : frag2, 'place2' : place2,
        'prev_frag1': prev_frag1, 'prev_place1': prev_place1,
        'prev_frag2': prev_frag2, 'prev_place2': prev_place2,
        'next_frag1': next_frag1, 'next_place1': next_place1,
        'next_frag2': next_frag2, 'next_place2': next_place2,
        'max_place': str(max_place), 'max_segment': str(max_segment),
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
