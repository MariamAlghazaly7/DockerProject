from pipes import Template
from django.shortcuts import render

from django.views.generic import ListView, DetailView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
import requests
from django.http import JsonResponse
from django.urls import reverse
from django.urls import reverse_lazy
import uuid

from people.models import MissingPerson, ReportedPerson
from .forms import *
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView

import json

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.mail import send_mail

# to get api credentials
with open('./config.json', 'r') as f:
    config = json.load(f)


## MISSING PERSONS
# view to list all missing people
class MissingPersonListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = MissingPerson
    template_name = 'people/missing_person_list.html'
    context_object_name = "missing_persons"

# to view list of all missing people who need to be approved/verified
class MissingPersonToBeApprovedListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    template_name = 'people/missing_person_list.html'
    context_object_name = 'missing_persons'
    queryset = MissingPerson.objects.filter(is_verified=False)

# to view list of all missing people with status as leads (possible match with a reported person)
class MissingPersonWithLeadsListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    template_name = 'people/missing_person_list.html'
    context_object_name = 'missing_persons'
    queryset = MissingPerson.objects.filter(status='Leads')

# to view list of all missing people who have been found
class MissingPersonFoundListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    template_name = 'people/missing_person_list.html'
    context_object_name = 'missing_persons'
    queryset = MissingPerson.objects.filter(status='Found')


class ImageFinderView(FormView):
    model = MissingPerson
    form_class = MissingFindByImagePersonCreateForm
    template_name = 'people/find_image_form.html'
    success_url = reverse_lazy('image-person-finder-form-success')

    def form_valid(self, form):
        # Get the uploaded file
        photo_file = form.cleaned_data['photo']

        # Make a copy of the file for the external API call
        temp_file = photo_file.file.read()
        file_extension = photo_file.name.split('.')[-1]  # Extract the file extension
        random_filename = f"{uuid.uuid4().hex}.{file_extension}"
        # Perform the POST request
        url = 'http://127.0.0.1:8000/upload-image/'  # Replace with your desired URL
        fetched_data = {}
        try:
            # Use the file copy for the request
            external_response = requests.post(
                url,
                files={'file': (random_filename, temp_file)},  # Provide a filename
            )
            external_response.raise_for_status()
            fetched_data = external_response.json()  # Parse JSON response
            print(fetched_data)
        except requests.RequestException as e:
            print(f"Error sending POST request: {e}")

        # Set `is_find_by_image` to True
        form.instance.is_find_by_image = True

        # Save the form instance (original file is untouched)
        self.object = form.save()

        # Store the fetched data in the session (or pass via URL)
        self.request.session['fetched_data'] = fetched_data

        return HttpResponseRedirect(self.get_success_url())
class MissingPersonFormSuccessView(TemplateView):
    template_name = 'people/image-person-finder-form-success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Retrieve fetched data from the session
        fetched_data = self.request.session.pop('fetched_data', {})  # Pop once
        context['fetched_data'] = fetched_data  # Pass it to the context
        print(f"Retrieved fetched_data from session: {fetched_data}")  # Debugging

        return context
        

class MissingPersonCreateView(CreateView):
    model = MissingPerson
    form_class = MissingPersonCreateForm
    template_name = 'people/create_update_form.html'
    success_url = reverse_lazy('missing_person_form_success')  # Ensure success_url is set

    def form_valid(self, form):
        print("Catching Form Valid Function")
        print("self: ", self)
        print("self.object: ", self.object)
        # Save the form instance
        response = super().form_valid(form)
        print("response: ", response)
        # Prepare data for the POST request
        post_data = {
            'file': self.object.photo,    # Replace with the actual field names
        }
        file_field = self.object.photo
        # Perform the POST request
        url = 'http://127.0.0.1:8000/upload-image/'  # Replace with your desired URL
        fetched_data = {}
        try:
            # Open the file to send it as part of the request
            with file_field.open('rb') as file:
                # Perform the POST request
                external_response = requests.post(
                    url,
                    files={'file': file},  
                )
                external_response.raise_for_status()
                fetched_data = external_response.json()  # Parse JSON response
                print(fetched_data)
        except requests.RequestException as e:
            print(f"Error sending POST request: {e}")

        # Store the fetched data in the session (or pass via URL)
        self.request.session['fetched_data'] = fetched_data

        return HttpResponseRedirect(self.get_success_url())

        # Redirect to the success URL
        # return JsonResponse({'redirect': reverse('missing_person_form_success')})




# view to update a missing person
class MisssingPersonUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = MissingPerson
    form_class = MissingPersonUpdateForm
    template_name = 'people/create_update_form.html'
    success_url = reverse_lazy ('list_missing_person')

# function to generate face_id using Azure Face API
def generate_face_id(image_path):
    face_client = FaceClient(config['ENDPOINT'], CognitiveServicesCredentials(config['KEY']))
    response_detected_face = face_client.face.detect_with_stream(
        image=open(image_path, 'rb'),
        detection_model='detection_03',
        recognition_model='recognition_04',
        )
    return response_detected_face

# function to find a match for the reported person from the list of missing people using Azure Face API
def find_match(reported_face_id, missing_face_ids):
    face_client = FaceClient(config['ENDPOINT'], CognitiveServicesCredentials(config['KEY']))
    matched_faces = face_client.face.find_similar(
        face_id=reported_face_id,
        face_ids=missing_face_ids
        )
    return matched_faces

# view to verify a missing person (if background check is done)
class MisssingPersonVerifyView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = MissingPerson
    form_class = MissingPersonVerifyForm
    template_name = 'people/create_update_form.html'
    success_url = reverse_lazy ('list_missing_person')

    def post(self, request, **kwargs):
        print ("Catching Update Function")
            
        form = self.form_class(request.POST)
        if form.is_valid():
            if form.cleaned_data['is_verified']:
                self.object = self.get_object()
                print ("image URL is", self.object.photo.url)
                print ("image Path is", self.object.photo.path)
                
                print("face ID is",self.object.face_id)

                # if the person is verified and does not already have a face id, we generate one
                if not self.object.face_id:
                    print ("Calling Face ID Generation")

                    # generating face id
                    response_detected_face=generate_face_id(self.object.photo.path)
                    print ("Detected Face ID is",response_detected_face[0].face_id)

                    # saving the generated face id to database
                    self.object.face_id = response_detected_face[0].face_id
                    self.object.save()
        return super().post(request, **kwargs)

# view to delete a missing person
class MisssingPersonDeleteView(LoginRequiredMixin, DeleteView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = MissingPerson
    template_name = 'people/delete_form.html'
    success_url = reverse_lazy ('list_missing_person')

## REPORTED PERSONS
# view to list all reported people
class ReportedPersonListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = ReportedPerson
    template_name = 'people/reported_person_list.html'
    context_object_name = "reported_persons"

# to view list of all reported people who need to be approved/verified
class ReportedPersonToBeApprovedListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    template_name = 'people/reported_person_list.html'
    context_object_name = 'reported_persons'
    queryset = ReportedPerson.objects.filter(is_verified=False)

# to view list of all reported people who have been matched with a missing person
class ReportedPersonMatchedListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    template_name = 'people/reported_person_list.html'
    context_object_name = 'reported_persons'
    queryset = ReportedPerson.objects.filter(is_matched_with_missing_person=True)


# to view list of all reported people who have not yet been matched with a missing person
class ReportedPersonNotMatchedListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    template_name = 'people/reported_person_list.html'
    context_object_name = 'reported_persons'
    queryset = ReportedPerson.objects.filter(is_matched_with_missing_person=False, is_verified=True)

# view to create reported people
class ReportedPersonCreateView(CreateView):
    model = ReportedPerson
    form_class = ReportedPersonCreateForm
    template_name = 'people/reported_create_update_form.html'
    success_url = reverse_lazy ('reported_person_form_success')

# view to update reported people
class ReportedPersonUpdateView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = ReportedPerson
    form_class = ReportedPersonUpdateForm
    template_name = 'people/reported_create_update_form.html'
    success_url = reverse_lazy ('list_reported_person')

# view to verify a reported person 
class ReportedPersonVerifyView(LoginRequiredMixin, UpdateView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = ReportedPerson
    form_class = ReportedPersonVerifyForm
    template_name = 'people/reported_create_update_form.html'
    success_url = reverse_lazy ('list_reported_person')

    def post(self, request, **kwargs):
        print ("Catching Update Function")
            
        form = self.form_class(request.POST)
        if form.is_valid():
            if form.cleaned_data['is_verified']:
                self.object = self.get_object()
                print ("image URL is", self.object.photo.url)
                print ("image Path is", self.object.photo.path)
                
                print("face ID is",self.object.face_id)
                
                # to get a list of all face_ids of missing persons
                missing_persons_face_ids = list(MissingPerson.objects.filter(face_id__isnull=False).values_list('face_id', flat=True))
                # missing_persons_names = list(MissingPerson.objects.all().values_list('first_name', flat=True))
                # db = dict(zip(missing_persons_names, missing_persons_face_ids))

                # if the person is verified and does not already have a face id, we generate one
                if not self.object.face_id:
                    print ("Calling Face ID Generation")

                    # generating face id
                    response_detected_face=generate_face_id(self.object.photo.path)
                    print ("Detected Face ID is",response_detected_face[0].face_id)

                    # saving the generated face id to database
                    self.object.face_id = response_detected_face[0].face_id
                    self.object.save()

                    # finding if there is a match
                    matched_faces=find_match(self.object.face_id, missing_persons_face_ids)

                    print(matched_faces)
                    # if return list is not empty
                    if len(matched_faces)!=0:
                        # if the matched face returned exists in list of missing people
                        if MissingPerson.objects.filter(face_id=matched_faces[0].face_id).exists():
                            print ("match found !")
                            print (matched_faces[0].face_id, matched_faces[0].confidence)
                            
                            # getting the matched missing person
                            found_person = MissingPerson.objects.get(face_id = matched_faces[0].face_id)
                            found_person.status="Leads"
                            found_person.found_location=self.object.reported_location
                            found_person.found_time=self.object.created_date
                            
                            found_person.save()

                            # Updating matched details to reported database
                            self.object.matched_face_id = matched_faces[0].face_id
                            self.object.is_matched_with_missing_person = True
                            self.object.matched_confindence = "This could be " + found_person.first_name + " lost at " + found_person.last_seen + " reported by "+ found_person.contact_person +  " with confidence rate of " + str(matched_faces[0].confidence*100) +"%." 
                            self.object.save()

        return super().post(request, **kwargs)
    


# motaz
class ClearModelImagesSuccessView(TemplateView):
    template_name = 'people/clear_model_images_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Retrieve the response message from the session
        fetched_data = self.request.session.pop('fetched_data', {})  # Pop once
        print("from success clear: ", fetched_data)
        context['fetched_data'] = fetched_data
        print(f"Retrieved fetched_data from session: {fetched_data}")  # Debugging
        return context
    
class ClearModelImages(LoginRequiredMixin, TemplateView):
    model = ReportedPerson
    form_class = ReportedPersonVerifyForm
    template_name = 'people/clear_model_images.html'
    success_url = reverse_lazy ('clear_model_images_success')

    def post(self, request, *args, **kwargs):
        # URL of the external API endpoint
        api_url = 'http://127.0.0.1:8000/clear-images/'
        delete_from_db = request.POST.get('delete_from_db') == 'on'
        try:
            # Perform the DELETE request
            response = requests.delete(api_url)
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses
            fetched_data = response.json()  # Parse JSON response
            print("fetched_data of deleyeee::: ", fetched_data)
            # If the request is successful, redirect to the success URL
            if delete_from_db:
                MissingPerson.objects.filter(is_find_by_image=True).delete()

            if response.status_code == 204:
                response_message = "All records have been deleted successfully!"
            else:
                # Fallback message if response status is not 204 but still successful
                response_message = response.json().get('message', 'Operation completed successfully.')
            request.session['fetched_data'] = {'message': response_message}
            return HttpResponseRedirect(self.success_url)
        except requests.RequestException as e:
            # Handle errors (e.g., log them, show a message to the user, etc.)
            print(f"Error during DELETE request: {e}")

        # If the request fails, reload the page or show an error
        return self.render_to_response(self.get_context_data(error="Failed to delete resource"))


# view to delete reported person
class ReportedPersonDeleteView(LoginRequiredMixin, DeleteView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = ReportedPerson
    template_name = 'people/delete_form.html'
    success_url = reverse_lazy ('list_reported_person')

# view to display matched/found person details
class FoundPersonTemplateView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('index')
    logout_url = reverse_lazy('index')
    model = MissingPerson
    template_name = 'people/found_person_details.html'
    

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context['reported_person_details'] = ReportedPerson.objects.filter(matched_face_id = self.kwargs['face_id'] )
        
        context['found_person_details'] = MissingPerson.objects.filter(face_id = self.kwargs['face_id'] )
        return context

# view to display missing person has been successfully registered

    


# view to display reported person has been successfully registered
class ReportedPersonFormSuccessView(TemplateView):
    template_name= 'people/reported_person_form_success.html'

# fuction to send contact person a mail
def SendEmailToContact(object):
    subject = f'We have found {object.first_name}!'
    message = f'Hi {object.contact_person}, {object.first_name} {object.last_name} was reported to be found at {object.found_location} on {object.found_time}.'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [object.contact_email, ]
    send_mail( subject, message, email_from, recipient_list )

# function to set status as found and send email to contact person when "Confirm and match" button is clicked
def missing_person_update_status(request, pk):
    object = get_object_or_404(MissingPerson, pk=pk)
    object.status = "Found"
    # contacting the relative/guardian
    SendEmailToContact(object)
    object.is_contacted = True
    object.save()
    print("Email sent!")
    context = {'missing_person_object': object}

    return render(request, "people/missing_person_matched.html", context)