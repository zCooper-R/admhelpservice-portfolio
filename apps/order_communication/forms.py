from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return [single_file_clean(data, initial)]


class BaseOrderMessageForm(forms.Form):
    body = forms.CharField(
        required=True,
        max_length=5000,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "form-control order-thread__textarea",
                "placeholder": "Напишите сообщение",
            }
        ),
    )
    attachments = MultipleFileField(required=False, label="Файлы")

    def clean_attachments(self):
        files = self.cleaned_data.get("attachments") or []
        max_files = 5
        max_file_size = 10 * 1024 * 1024

        if len(files) > max_files:
            raise forms.ValidationError(f"Можно приложить не более {max_files} файлов.")

        for file_obj in files:
            if file_obj.size > max_file_size:
                raise forms.ValidationError("Размер каждого файла должен быть не больше 10 МБ.")
        return files


class OrderPublicReplyForm(BaseOrderMessageForm):
    pass


class OrderInternalNoteForm(BaseOrderMessageForm):
    pass
