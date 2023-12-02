from django.shortcuts import render, get_object_or_404
from .models import Snippet, UserSnippet
from django.contrib.auth.decorators import login_required
from django.db.models import F

@login_required
def display_snippets(request):
    # Default values
    segment_id = 1
    place1 = 1
    place2 = 2

    snippet1 = get_object_or_404(Snippet, segment_id=segment_id, place=place1)
    snippet2 = get_object_or_404(Snippet, segment_id=segment_id, place=place2)

    user_snippet1, created = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet1)
    user_snippet2, created = UserSnippet.objects.get_or_create(user=request.user, snippet=snippet2)

    prev_snippet = Snippet.objects.filter(segment_id=segment_id, place=F('place') - 1).first()

    context = {
        'snippet1': snippet1,
        'snippet2': snippet2,
        'user_snippet1': user_snippet1,
        'user_snippet2': user_snippet2,
        'prev_snippet': prev_snippet
    }

    return render(request, 'snippets_display.html', context)