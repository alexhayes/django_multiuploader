import os
import json
from django.views.generic.detail import DetailView
from django.utils.importlib import import_module
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import force_text
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponse, HttpResponseRedirect,\
    HttpResponseBadRequest
from django.views.generic.base import View

JSON_ENCODER = getattr(settings, 'JSON_ENCODER', False)
if JSON_ENCODER:
    parts = JSON_ENCODER.split('.')
    module = import_module('.'.join(parts[:-1]))
    JSON_ENCODER = getattr(module, parts[-1:][0])
else:
    JSON_ENCODER = DjangoJSONEncoder

class MultiuploaderMixin():
    """
    A mixin that can be used to produce a list of files suitable for json consumption.
    """
    multiuploader_queryset = None
    multiuploader_model = None
    multiuploader_field_name = None
    multiuploader_delete_type = 'POST'

    def get_multiuploader_model(self):
        if self.multiuploader_model:
            return self.multiuploader_model
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a Multiuploader Model. Define "
                "%(cls)s.multiuploader_model or override "
                "%(cls)s.get_multiuploader_model()." % {
                    'cls': self.__class__.__name__
                }
            )

    def get_multiuploader_queryset(self):
        """
        Return the `QuerySet` that will be used to look up the object.

        Note that this method is called by the default implementation of
        `get_object` and may not be called if `get_object` is overriden.
        """
        if self.multiuploader_queryset is None:
            if self.multiuploader_model:
                return self.multiuploader_model._default_manager.all()
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a Multiuploader QuerySet. Define "
                    "%(cls)s.multiuploader_model, %(cls)s.multiuploader_queryset, or override "
                    "%(cls)s.get_multiuploader_queryset()." % {
                        'cls': self.__class__.__name__
                    }
                )
        return self.multiuploader_queryset.all()

    def get_multiuploader_field_name(self):
        if self.multiuploader_field_name is None:
            raise ImproperlyConfigured(
                "%(cls)s is missing a Multiuploader field name. Define "
                "%(cls)s.multiuploader_field_name or override "
                "%(cls)s.get_multiuploader_field_name()." % {
                    'cls': self.__class__.__name__
                }
            )
        return self.multiuploader_field_name

    def single_obj_context_data(self, obj, wrap=True):
        field = getattr(obj, self.get_multiuploader_field_name())
        return {
            'id': obj.pk,
            'class': obj.__class__.__name__,
            'name': os.path.basename(field.name),
            'size': field.size,
            'url': obj.get_download_url() if hasattr(obj, 'get_download_url') else None,
            'delete_url': obj.get_delete_url() if hasattr(obj, 'get_delete_url') else None,
            'delete_type': self.multiuploader_delete_type,
            'thumbnail_url': obj.get_thumbnail_url() if hasattr(obj, 'get_thumbnail_url') else None
        }

    def list_context_data(self, **kwargs):
        context = [self.single_obj_context_data(obj) 
                   for obj in self.get_multiuploader_queryset()]
        return context

    def context_wrapper(self, context):
        if isinstance(context, dict):
            context = [context]
        return {
            'files': context
        }

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response, using the `response_class` for this
        view, with a template rendered with the given context.

        If any keyword arguments are provided, they will be
        passed to the constructor of the response class.
        """
        return HttpResponse(json.dumps(self.context_wrapper(context), cls=JSON_ENCODER), 
                            content_type='application/json',
                            **response_kwargs)
    
class MultiuploaderListForObjectView(DetailView, MultiuploaderMixin):
    """
    Render a list of files for an object.

    By default this is a model instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    
    `multiuploader_relationship_name` defines the relationship between `self.get_object()`
    and any uploaded files. By default this is set to 'attachments'.
    """
    multiuploader_queryset_name = 'attachments'
    
    def get_context_data(self, **kwargs):
        return self.list_context_data()
    
    def get_multiuploader_queryset_name(self):
        return self.multiuploader_queryset_name
    
    def get_multiuploader_queryset(self):
        obj = self.get_object()
        multiuploader_queryset_name = self.get_multiuploader_queryset_name()
        
        if not hasattr(obj.objects, multiuploader_queryset_name):
            raise ImproperlyConfigured(
                "%(cls)s has not defined %(multiuploader_queryset_name)s. Perhaps "
                    "%(cls)s.multiuploader_queryset_name is configured incorrectly?" % {
                        'cls': self.__class__.__name__,
                        'multiuploader_queryset_name': multiuploader_queryset_name
                    }
                )
        return getattr(obj.objects, self.multiuploader_queryset_name).all()

class MultiuploaderDetailView(MultiuploaderMixin, DetailView):
    
    def get_context_data(self, **kwargs):
        return self.single_obj_context_data(self.get_object())

class MultiuploaderCreateView(View, MultiuploaderMixin):
    """
    A mixin to handle uploads from the multi-uploader client-side code.
    """
    multiuploader_form_field_name = 'files'
    multiuploader_save = True
    success_url = None
    
    def post(self, request, **kwargs):
        self.obj = self.augment_upload(self.handle_upload())
        return HttpResponseRedirect(self.get_success_url())
    
    def handle_upload(self):
        """
        Handle the upload of a single file.
        """
        # Create our model that represents the file
        obj = self.get_multiuploader_model()()
        setattr(obj, self.get_multiuploader_field_name(), self.get_uploaded_file())
        return self.augment_upload(obj)
    
    def get_uploaded_file(self):
        if self.request.FILES == None:
            return HttpResponseBadRequest('No files attached.')

        # Get the uploaded file - note there is only a single file, even though its called xxx[]
        return self.request.FILES[u'%s[]' % self.multiuploader_form_field_name]

    def augment_upload(self, obj):
        if self.multiuploader_save:
            obj.save()
        return obj

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return url

class MultiuploaderCreateForObjectView(MultiuploaderCreateView, MultiuploaderListForObjectView):
    """
    Upload a file and add it to a particular relationship as defined by DetailView. 
    """

    def augment_upload(self, f):
        obj = self.get_object()
        getattr(obj, self.multiuploader_relationship_name).add(f)
        return f
