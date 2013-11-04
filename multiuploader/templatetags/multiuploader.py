from django import template
from django.conf import settings
from django.core.urlresolvers import reverse

register = template.Library()

@register.inclusion_tag('multiuploader/multiuploader_main.html')
def multiuploader(create_view=None, list_view=None, create_url=None, list_url=None, **view_kwargs):
    context = {
        'static_url': settings.STATIC_URL
    }
    
    if create_url is not None:
        context['create_url'] = create_url
    elif create_view is not None:
        context['create_url'] = reverse(create_view, kwargs=view_kwargs)
    
    if list_url is not None:
        context['list_url'] = list_url
    elif list_view is not None:
        context['list_url'] = reverse(list_view, kwargs=view_kwargs)

    return context