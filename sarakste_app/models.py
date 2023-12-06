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
    text = models.TextField(help_text='The written text in the image of the snippet.', null=True, blank=True)
    summary = models.ForeignKey(Summary, on_delete=models.SET_NULL, null=True, blank=True)  # Corrected ForeignKey
    users = models.ManyToManyField(User, through='UserSnippet')
    overlaprowcount = models.IntegerField(null=True, blank=True, default=0, help_text='The number of rows from this image that overlap on the next image in the segment.')
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