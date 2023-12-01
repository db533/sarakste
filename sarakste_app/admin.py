from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Segment)
admin.site.register(Summary)
admin.site.register(Snippet)
admin.site.register(UserSnippet)
