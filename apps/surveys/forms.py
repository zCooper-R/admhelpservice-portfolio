from django import forms


class SurveySubmissionRequestForm(forms.Form):
    campaign_id = forms.IntegerField(min_value=1)
    answers = forms.JSONField(required=False)

    def clean_answers(self):
        answers = self.cleaned_data["answers"]
        if answers is None:
            return []
        if not isinstance(answers, list):
            raise forms.ValidationError("Поле answers должно быть массивом.")
        return answers
