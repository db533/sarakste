from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta, time

class Segment(models.Model):
    length = models.IntegerField(null=True, default=0)
    validated = models.BooleanField(default=False)

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
    filename = models.CharField(max_length=50, help_text='The filename of the image for the snippet.')
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
    validated = models.BooleanField(default=False)
    precisedate = models.DateField(default=None, null=True, blank=True, verbose_name = 'Precīzs datums sarakstei', help_text='Precīzs datums sarakstei')
    filename_prior = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, related_name='prior_filename')
    filename_next = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, related_name='next_filename')


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
    reply_to_text = models.TextField(help_text='Teksts kam tika atbildēts', null=True, blank=True)
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
    mse_score = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    ssim_score = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    time_diff = models.TimeField(help_text=('Laiks atšķirība'),null=True,blank=True)

    def compute_time_diff(self):
        # Check if either time is None
        if not self.first_snippet.last_time or not self.second_snippet.first_time:
            self.time_diff = None
            return

        # Convert time fields to datetime objects for calculation
        datetime_format = "%H:%M:%S"
        last_time = datetime.strptime(str(self.first_snippet.last_time), datetime_format)
        first_time = datetime.strptime(str(self.second_snippet.first_time), datetime_format)

        # Check if the time indicates next day
        if first_time < last_time:
            first_time += timedelta(days=1)

        # Calculate time difference
        time_diff = first_time - last_time

        # Convert time difference to time object
        total_seconds = int(time_diff.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.time_diff = time(hour=hours, minute=minutes, second=seconds)  # Corrected

    def save(self, *args, **kwargs):
        self.compute_time_diff()  # Compute time_diff before saving
        super().save(*args, **kwargs)  # Call the "real" save() method.
    def __str__(self):
        return f"{self.id}"
