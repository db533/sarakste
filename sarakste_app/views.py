from django.shortcuts import render, get_object_or_404
from .models import *
from django.contrib.auth.decorators import login_required
from django.db.models import F

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
            summary1_text = request.POST.get('summary1', '').strip()
            if summary1_text:
                summary1, _ = Summary.objects.get_or_create(title=summary1_text)
                snippet1.summary = summary1
            else:
                snippet1.summary = None
            snippet1.save()

        if snippet2 is not None:
            snippet2.text = request.POST.get('text2', '')
            summary2_text = request.POST.get('summary2', '').strip()
            if summary2_text:
                summary2, _ = Summary.objects.get_or_create(title=summary2_text)
                snippet2.summary = summary2
            else:
                snippet2.summary = None
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
        return redirect(f'/lasit/?frag1={frag1}&place1={place1}&frag2={frag2}&place2={place2}&edit={edit_mode}&saved=true')

    prev_snippet = Snippet.objects.filter(segment_id=frag1, place=F('place') - 1).first()
    if int(place1) > 1:
        prev_snippet_exists = True
    else:
        prev_snippet_exists = False

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
    }

    return render(request, 'snippets_display.html', context)
