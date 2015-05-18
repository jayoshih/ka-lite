import os

from random import randint

from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from tastypie import fields
from tastypie.exceptions import NotFound, Unauthorized
from tastypie.resources import ModelResource, Resource

from fle_utils.config.models import Settings
from fle_utils.internet import api_handle_error_with_json

from kalite.shared.api_auth import UserObjectsOnlyAuthorization
from kalite.facility.api_resources import FacilityUserResource
from kalite.facility.models import Facility
from kalite.ab_testing.data.groups import get_grade_by_facility, GRADE_BY_FACILITY as GRADE

from .models import Test, TestLog

from django.conf import settings

logging = settings.LOG

class UserTestObjectsOnlyAuthorization(UserObjectsOnlyAuthorization):

    def create_list(self, object_list, bundle):

        return super(UserTestObjectsOnlyAuthorization, self).create_list(object_list, bundle)

    def create_detail(self, object_list, bundle):

        return super(UserTestObjectsOnlyAuthorization, self).create_detail(object_list, bundle)

    def update_list(self, object_list, bundle):

        return super(UserTestObjectsOnlyAuthorization, self).update_list(object_list, bundle)

    def update_detail(self, object_list, bundle):

        return super(UserTestObjectsOnlyAuthorization, self).update_detail(object_list, bundle)

class TestLogResource(ModelResource):

    def wrap_view(self, view):
        """
        Wraps views to return custom error codes instead of generic 500's
        """
        def wrapper(request, *args, **kwargs):
            try:
                callback = getattr(self, view)
                response = callback(request, *args, **kwargs)

                # response is a HttpResponse object, so follow Django's instructions
                # to change it to your needs before you return it.
                # https://docs.djangoproject.com/en/dev/ref/request-response/
                return response
            except Exception as e:
                # Rather than re-raising, we're going to things similar to
                # what Django does. The difference is returning a serialized
                # error message.
                return self._handle_500(request, e)

        return wrapper

    user = fields.ForeignKey(FacilityUserResource, 'user')

    class Meta:
        queryset = TestLog.objects.all()
        resource_name = 'testlog'
        filtering = {
            "test": ('exact', ),
            "user": ('exact', ),
        }
        authorization = UserTestObjectsOnlyAuthorization()


class TestResource(Resource):

    title = fields.CharField(attribute='title')
    ids = fields.CharField(attribute='ids')
    playlist_ids = fields.CharField(attribute='playlist_ids')
    seed = fields.IntegerField(attribute='seed')
    repeats = fields.IntegerField(attribute='repeats')
    test_id = fields.CharField(attribute='test_id')
    test_url = fields.CharField(attribute='test_url')

    class Meta:
        resource_name = 'test'
        object_class = Test

    def _read_test(self, test_id, force=False):
        testscache = Test.all(force=force)
        return testscache.get(test_id, None)

    def _read_tests(self, test_id=None, force=False):
        testscache = Test.all(force=force)
        return sorted(testscache.values(), key=lambda test: test.title)

    def _read_facility_tests(self, facility, test_id=None, force=False):
        testscache = Test.all(force=force)
        valid_tests = dict((id, test) for (id, test) in testscache.iteritems() if test.grade == get_grade_by_facility(facility))
        return sorted(valid_tests.values(), key=lambda test: test.title)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<test_id>[\w\d_.-]+)/$" % self._meta.resource_name,
                self.wrap_view('dispatch_detail'),
                name="api_dispatch_detail"),
        ]

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}
        if getattr(bundle_or_obj, 'obj', None):
            kwargs['pk'] = bundle_or_obj.obj.test_id
        else:
            kwargs['pk'] = bundle_or_obj.test_id
        return kwargs

    def get_object_list(self, request, force=False):
        if 'facility_user' in request.session:
            facility = request.session['facility_user'].facility
            return self._read_facility_tests(facility, force=force,)
        return self._read_tests(force=force)

    def obj_get_list(self, bundle, **kwargs):
        force = bundle.request.GET.get('force', False)
        return self.get_object_list(bundle.request, force=force)

    def obj_get(self, bundle, **kwargs):
        test_id = kwargs.get("test_id", None)
        test = self._read_test(test_id)
        if test:
            return test
        else:
            raise NotFound('Test with test_id %s not found' % test_id)

    def obj_create(self, request):
        raise NotImplemented("Operation not implemented yet for tests.")

    def obj_update(self, bundle, **kwargs):
        raise NotImplemented("Operation not implemented yet for tests.")

    def obj_delete_list(self, request):
        raise NotImplemented("Operation not implemented yet for tests.")

    def obj_delete(self, request):
        raise NotImplemented("Operation not implemented yet for tests.")

    def rollback(self, request):
        raise NotImplemented("Operation not implemented yet for tests.")
