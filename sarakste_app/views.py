from django.shortcuts import render, get_object_or_404
from .models import Snippet, UserSnippet
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


@login_required
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def display_snippets(request):
    # Default values
    segment_id = 1
    place1 = 1
    place2 = 2

    snippet1 = get_object_or_404(Snippet, segment_id=segment_id, place=place1)
    snippet2 = get_object_or_404(Snippet, segment_id=segment_id, place=place2)

    user_snippet1, _ = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet1)
    user_snippet2, _ = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet2)

    if request.method == 'POST':
        snippet1.text = request.POST.get('text1', '')
        snippet2.text = request.POST.get('text2', '')

        snippet1.summary = request.POST.get('summary1', '')
        snippet2.summary = request.POST.get('summary2', '')

        user_snippet1.loved = 'loved1' in request.POST
        user_snippet2.loved = 'loved2' in request.POST

        user_snippet1.marked = 'marked1' in request.POST
        user_snippet2.marked = 'marked2' in request.POST

        # Save the updated objects
        snippet1.save()
        snippet2.save()
        user_snippet1.save()
        user_snippet2.save()

        # Redirect to the same page to display updated content
        return redirect('display_snippets')

    prev_snippet = Snippet.objects.filter(segment_id=segment_id, place=F('place') - 1).first()

    context = {
        'snippet1': snippet1,
        'snippet2': snippet2,
        'user_snippet1': user_snippet1,
        'user_snippet2': user_snippet2,
        'prev_snippet': prev_snippet
    }

    return render(request, 'snippets_display.html', context)
