from django import template
from sarakste_app.models import Segment, Snippet

register = template.Library()

@register.inclusion_tag('segment_links.html')
def segment_links():
    segments = Segment.objects.all()
    segment_links = []
    for segment in segments:
        snippets = Snippet.objects.filter(segment=segment).order_by('place')[:2]
        length = segment.length
        if snippets.exists():
            url = "https://sarakste.digitalaisbizness.lv/lasit/?frag1={}&place1={}".format(segment.id, snippets[0].place)
            if snippets.count() > 1:
                url += "&frag2={}&place2={}".format(segment.id, snippets[1].place)
            segment_links.append((segment.id, url, length))
    return {'segment_links': segment_links}
