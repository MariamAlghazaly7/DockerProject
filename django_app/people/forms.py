
from django import forms

from people.models import MissingPerson, ReportedPerson
#Forms for the missing person db
class ImageUploadForm(forms.Form):
    file = forms.ImageField(
        label="Upload Image",
        required=True,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

class MissingPersonCreateForm(forms.ModelForm):
    class Meta:
        file = forms.ImageField(
        label="Upload Image",
        required=True,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    ) 
        model = MissingPerson
        # fields = "__all__"
        exclude = ['status', 'is_verified', 'face_id', 'found_location', 'found_time', 'is_contacted']    

        
class MissingFindByImagePersonCreateForm(forms.ModelForm):
    # file = forms.ImageField(
    # label="Upload Image",
    # required=True,
    # widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    # ) 
    class Meta:
    
        model = MissingPerson
        # fields = "__all__"
        exclude = ['status', 'is_verified', 'face_id', 'found_location', 'found_time', 'is_contacted']
        widgets = {
            'is_find_by_image': forms.HiddenInput(),  # Hide this field in the form
        }          


class MissingPersonUpdateForm(forms.ModelForm):
    class Meta:
        model = MissingPerson
        exclude = ['face_id', 'is_verified', 'found_location', 'found_time', 'is_contacted']
        # fields = "__all__"
        

class MissingPersonVerifyForm(forms.ModelForm):
    class Meta:
        model = MissingPerson
        # exclude = ['face_id']
        fields = ['is_verified']


#Forms for the reported person db
class ReportedPersonCreateForm(forms.ModelForm):
    class Meta:
        model = ReportedPerson
        # fields = "__all__"
        exclude = ['is_verified', 'face_id','is_matched_with_missing_person','matched_confindence', 'matched_face_id' ]


class ReportedPersonUpdateForm(forms.ModelForm):
    class Meta:
        model = ReportedPerson
        exclude = ['face_id']
        # fields = "__all__"
        

class ReportedPersonVerifyForm(forms.ModelForm):
    class Meta:
        model = ReportedPerson
        # exclude = ['face_id']
        fields = ['is_verified']