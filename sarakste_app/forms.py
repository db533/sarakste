from django import forms
from django.core.exceptions import ValidationError

class SearchForm(forms.Form):
    query = forms.CharField(label='Līdzīgu teksta meklējamā frāze', required=False)
    query_like = forms.CharField(label='Precīzi saturētā frāze pamatteikumā', required=False)
    query_like_reply = forms.CharField(label='Precīzi saturētā frāze atbildētā tekstā (reply_to_text)', required=False)
    query_like_filename = forms.CharField(label='Faila nosaukuma daļa', required=False)
    query_first_time = forms.TimeField(
        label='Pirmais laiks (HH:mm)',
        required=False,
        input_formats=['%H:%M'],
        help_text='Meklēt pēc laika formātā HH:mm'
    )
    query_last_time = forms.TimeField(
        label='Pēdējais laiks (HH:mm)',
        required=False,
        input_formats=['%H:%M'],
        help_text='Meklēt pēc laika formātā HH:mm'
    )

    def clean(self):
        cleaned_data = super().clean()
        query = cleaned_data.get("query")
        query_like = cleaned_data.get("query_like")
        query_like_reply = cleaned_data.get("query_like_reply")
        query_like_filename = cleaned_data.get("query_like_filename")
        query_first_time = cleaned_data.get("query_first_time")
        query_last_time = cleaned_data.get("query_last_time")


        # Check if both fields are empty
        if not query and not query_like and not query_like_reply and not query_like_filename and not query_first_time and not query_last_time:
            raise ValidationError("Vismaz vienu lauku jāaizpilda.")

        return cleaned_data
