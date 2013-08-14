from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    url(r'^$', 'post.views.list', name='home'),
    (r'^post/(.*)/$', 'post.views.post'),

    # Examples:
    # url(r'^$', 'exampleSettings.views.home', name='home'),
    # url(r'^exampleSettings/', include('exampleSettings.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    (r'^edit/(.*)/$', 'post.views.edit'),
    #captcha urls
    url(r'^captcha/', include('captcha.urls')),

    (r'^register/$', 'basiclogin.views.register'),


    #preview pages for the STL files.
    (r'^thumbs/stl/(.*)', 'thumbnailer.views.stlthumb'),
    (r'^preview/stl/(.*)', 'thumbnailer.views.stlview'),
    url(r'', include('multiuploader.urls')),

)+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


