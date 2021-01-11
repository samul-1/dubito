"""dubito URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from django.contrib import admin
from django.urls import include, path

from django.conf.urls import url
from django.views.i18n import JavaScriptCatalog
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('', include('dubitoapp.urls')),
    path('game/', include('dubitoapp.urls')),
    path('wugierqwetisfjoi14/', admin.site.urls),
]

js_info_dict = {
    'packages': ('dubitoapp',),
}

urlpatterns += i18n_patterns(
    path('jsi18n/', JavaScriptCatalog.as_view(packages=['dubitoapp'], domain="django"), name='javascript-catalog'),
    path('', include('dubitoapp.urls')),
)
