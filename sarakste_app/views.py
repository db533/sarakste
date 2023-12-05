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
    # Extract parameters from the request, using default values if not provided
    frag1 = request.GET.get('frag1', 1)
    place1 = request.GET.get('place1', 1)
    frag2 = request.GET.get('frag2', 1)
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
            if selected_summary1_id:
                selected_summary1 = Summary.objects.get(id=selected_summary1_id)
                snippet1.summary = selected_summary1
            elif new_summary1_title:
                new_summary1, _ = Summary.objects.get_or_create(title=new_summary1_title)
                snippet1.summary = new_summary1
            snippet1.save()

        if snippet2 is not None:
            snippet2.text = request.POST.get('text2', '')
            selected_summary2_id = request.POST.get('selected_summary2')
            new_summary2_title = request.POST.get('new_summary2', '').strip()
            if selected_summary2_id:
                selected_summary2 = Summary.objects.get(id=selected_summary2_id)
                snippet2.summary = selected_summary2
            elif new_summary2_title:
                new_summary2, _ = Summary.objects.get_or_create(title=new_summary2_title)
                snippet2.summary = new_summary2
            snippet2.save()

        if user_snippet1 is not None:
            user_snippet1.loved = 'loved1' in request.POST
            user_snippet1.marked = 'marked1' in request.POST
            user_snippet1.save()

        if user_snippet2 is not None:
            user_snippet2.loved = 'loved2' in request.POST
            user_snippet2.marked = 'marked2' in request.POST
            user_snippet2.save()

        # Redirect to the same page to display updated content
        #return redirect('display_snippets')
        snippet1.save()
        snippet2.save()
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
    if next_place1 > max_place:
            next_frag1 = int(frag1)+1
            next_place1 = 1

    next_frag2, next_place2 = frag2, int(place2) + 1
    if next_place2 > max_place:
        next_frag2 =int(frag2)+1
        next_place2 = 1

    context = {
        'snippet1': snippet1,
        'snippet2': snippet2,
        'user_snippet1': user_snippet1,
        'user_snippet2': user_snippet2,
        'prev_snippet': prev_snippet,
        'edit_mode': edit_mode,  # Add edit mode to context
        'prev_snippet_exists' : prev_snippet_exists,
        'frag1' : frag1,
        'place1' : place1,
        'frag2' : frag2,
        'place2' : place2,
        'prev_frag1': prev_frag1, 'prev_place1': prev_place1,
        'prev_frag2': prev_frag2, 'prev_place2': prev_place2,
        'next_frag1': next_frag1, 'next_place1': next_place1,
        'next_frag2': next_frag2, 'next_place2': next_place2,
        'max_place': str(max_place), 'max_segment': str(max_segment),
        'summaries': summaries,
    }

    return render(request, 'snippets_display.html', context)
