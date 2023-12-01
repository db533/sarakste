from django.db import models
from django.contrib.auth.models import User

class Segment(models.Model):
    length = models.IntegerField(null=True, default=0)

    def __str__(self):
        return str(self.id)

class Summary(models.Model):
    title = models.CharField(max_length=255, help_text='A title for an episode in the chat.')
    description = models.TextField(help_text='A longer description about the episode.')

    def __str__(self):
        return self.title

class Snippet(models.Model):
    place = models.IntegerField(null=True, blank=True, default=1, help_text='The position in the sequence.')
    target_url = models.CharField(max_length=255, help_text='The url to the image for the snippet.')
    filename = models.CharField(max_length=30, help_text='The filename of the image for the snippet.')
    text = models.TextField(help_text='The written text in the image of the snippet.')
    summary = models.ForeignKey(Summary, on_delete=models.SET_NULL, null=True)  # Corrected ForeignKey
    users = models.ManyToManyField(User, through='UserSnippet')

class UserSnippet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    snippet = models.ForeignKey(Snippet, on_delete=models.CASCADE)
    loved = models.BooleanField(default=False)
    marked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'snippet')  # Ensures that each user-snippet pair is unique

    def __str__(self):
        return f"{self.user.username} - {self.snippet.filename}"