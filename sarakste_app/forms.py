from django import forms
from django.core.exceptions import ValidationError

class SearchForm(forms.Form):
    query = forms.CharField(label='Līdzīgu teksta meklējamā frāze', required=False)
    query_like = forms.CharField(label='Precīzi saturētā frāze pamatteikumā', required=False)
    query_like_reply = forms.CharField(label='Precīzi saturētā frāze atbildētā tekstā (reply_to_text)', required=False)

    def clean(self):
        cleaned_data = super().clean()
        query = cleaned_data.get("query")
        query_like = cleaned_data.get("query_like")
        query_like_reply = cleaned_data.get("query_like_reply")

        # Check if both fields are empty
        if not query and not query_like and not query_like_reply:
            raise ValidationError("Vismaz vienu lauku jāaizpilda.")

        return cleaned_data
