from django import template
from itertools import zip_longest

register = template.Library()

@register.filter(name='zip_longest')
def zip_longest_filter(list1, list2):
    return zip_longest(list1, list2)
