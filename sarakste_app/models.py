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
    segment = models.ForeignKey(Segment, on_delete=models.SET_NULL, null=True)  # Corrected ForeignKey
    # target_url = models.CharField(max_length=255, help_text='The url to the image for the snippet.', null=True)
    filename = models.CharField(max_length=30, help_text='The filename of the image for the snippet.')
    summary = models.ForeignKey(Summary, on_delete=models.SET_NULL, null=True, blank=True)  # Corrected ForeignKey
    users = models.ManyToManyField(User, through='UserSnippet')
    #overlaprowcount = models.IntegerField(null=True, blank=True, default=0, help_text='The number of rows from this image that overlap on the next image in the segment.')

    DAY_OF_WEEK = (
        ('1', 'Pirmdiena'),
        ('2', 'Otrdiena'),
        ('3', 'Trešdiena'),
        ('4', 'Ceturtdiena'),
        ('5', 'Piektdiena'),
        ('6', 'Sestdiena'),
        ('7', 'Svētdiena'),
    )
    weekday = models.CharField(max_length=1, choices=DAY_OF_WEEK, null=True, blank=True,
                               help_text='Nēdēļas diena',
                               verbose_name=('Nēdēļas diena'))
    first_time = models.TimeField(
        help_text=('Pirmā rakstītā teikuma laiks'),
        null=True,
        blank=True
    )
    last_time = models.TimeField(
        help_text=('Pēdējā rakstītā teikuma laiks'),
        null=True,
        blank=True
    )


class UserSnippet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    snippet = models.ForeignKey(Snippet, on_delete=models.CASCADE)
    loved = models.BooleanField(default=False)
    marked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'snippet')  # Ensures that each user-snippet pair is unique

    def __str__(self):
        return f"{self.user.username} - {self.snippet.filename}"

class Sentence(models.Model):
    SPEAKERS = (
        ('0', 'Dacīte'),
        ('1', 'Dainis'),
    )
    speaker = models.CharField(max_length=1, choices=SPEAKERS, default='0',
                               help_text='Kurš rakstīja šo teikumu',
                               verbose_name=('Teikuma autors'))
    text = models.TextField(help_text='Rakstītais teikums', null=True, blank=True)
    snippet = models.ForeignKey(Snippet, on_delete=models.CASCADE)
    sequence = models.IntegerField(help_text='The position of this sentence in the Snippet.')
    confidence = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    date = models.DateField(
        help_text=('Datums, kad teikums tika izrunāts'),
        null=True,
        blank=True
    )
    time = models.TimeField(
        help_text=('Laiks, kad teikums tika rakstīts'),
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.get_speaker_display()}: {self.text[:50]}..."

class SnippetOverlap(models.Model):
    first_snippet = models.ForeignKey(Snippet, related_name='current_overlaps', on_delete=models.CASCADE, help_text='The first snippet in the comparison.')
    second_snippet = models.ForeignKey(Snippet, related_name='overlapping_snippets', on_delete=models.CASCADE, help_text='The second snippet int he comparison.')
    overlaprowcount = models.IntegerField(default=0, help_text='The number of rows from this image that overlap on the next image.')

    def __str__(self):
        return f"{self.current_snippet.filename} overlaps {self.overlapping_snippet.filename}: {self.overlaprowcount} rows"
