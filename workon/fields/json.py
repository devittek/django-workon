
try:
    from django.contrib.postgres.fields import JSONField
    
except ImportError:
    
    import copy
    from django.db import models
    from django.utils.translation import ugettext_lazy as _

    try:
        import json
    except ImportError:
        from django.utils import simplejson as json

    from django.forms import fields
    try:
        from django.forms.utils import ValidationError
    except ImportError:
        from django.forms.util import ValidationError

    # This file was copied from django.db.models.fields.subclassing so that we could
    # change the Creator.__set__ behavior. Read the comment below for full details.

    """
    Convenience routines for creating non-trivial Field subclasses, as well as
    backwards compatibility utilities.

    Add SubfieldBase as the __metaclass__ for your Field subclass, implement
    to_python() and the other necessary methods and everything will work seamlessly.
    """


    class SubfieldBase(type):
        """
        A metaclass for custom Field subclasses. This ensures the model's attribute
        has the descriptor protocol attached to it.
        """
        def __new__(cls, name, bases, attrs):
            new_class = super(SubfieldBase, cls).__new__(cls, name, bases, attrs)
            new_class.contribute_to_class = make_contrib(
                new_class, attrs.get('contribute_to_class')
            )
            return new_class


    class Creator(object):
        """
        A placeholder class that provides a way to set the attribute on the model.
        """
        def __init__(self, field):
            self.field = field

        def __get__(self, obj, type=None):
            if obj is None:
                return self
            return obj.__dict__[self.field.name]

        def __set__(self, obj, value):
            # Usually this would call to_python, but we've changed it to pre_init
            # so that we can tell which state we're in. By passing an obj,
            # we can definitively tell if a value has already been deserialized
            # More: https://github.com/bradjasper/django-jsonfield/issues/33
            obj.__dict__[self.field.name] = self.field.pre_init(value, obj)


    def make_contrib(superclass, func=None):
        """
        Returns a suitable contribute_to_class() method for the Field subclass.

        If 'func' is passed in, it is the existing contribute_to_class() method on
        the subclass and it is called before anything else. It is assumed in this
        case that the existing contribute_to_class() calls all the necessary
        superclass methods.
        """
        def contribute_to_class(self, cls, name):
            if func:
                func(self, cls, name)
            else:
                super(superclass, self).contribute_to_class(cls, name)
            setattr(cls, self.name, Creator(self))

        return contribute_to_class
    from django.db.models.query import QuerySet
    from django.utils import timezone
    from django.utils.encoding import force_text
    from django.utils.functional import Promise
    import datetime
    import decimal
    import json
    import uuid


    class JSONEncoder(json.JSONEncoder):
        """
        JSONEncoder subclass that knows how to encode date/time/timedelta,
        decimal types, generators and other basic python objects.
        Taken from https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/utils/encoders.py
        """
        def default(self, obj):  # noqa
            # For Date Time string spec, see ECMA 262
            # http://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
            if isinstance(obj, Promise):
                return force_text(obj)
            elif isinstance(obj, datetime.datetime):
                representation = obj.isoformat()
                if obj.microsecond:
                    representation = representation[:23] + representation[26:]
                if representation.endswith('+00:00'):
                    representation = representation[:-6] + 'Z'
                return representation
            elif isinstance(obj, datetime.date):
                return obj.isoformat()
            elif isinstance(obj, datetime.time):
                if timezone and timezone.is_aware(obj):
                    raise ValueError("JSON can't represent timezone-aware times.")
                representation = obj.isoformat()
                if obj.microsecond:
                    representation = representation[:12]
                return representation
            elif isinstance(obj, datetime.timedelta):
                return str(obj.total_seconds())
            elif isinstance(obj, decimal.Decimal):
                # Serializers will coerce decimals to strings by default.
                return float(obj)
            elif isinstance(obj, uuid.UUID):
                return str(obj)
            elif isinstance(obj, QuerySet):
                return tuple(obj)
            elif hasattr(obj, 'tolist'):
                # Numpy arrays and array scalars.
                return obj.tolist()
            elif hasattr(obj, '__getitem__'):
                try:
                    return dict(obj)
                except:
                    pass
            elif hasattr(obj, '__iter__'):
                return tuple(item for item in obj)
            return super(JSONEncoder, self).default(obj)


    class JSONFormFieldBase(object):
        def __init__(self, *args, **kwargs):
            self.load_kwargs = kwargs.pop('load_kwargs', {})
            super(JSONFormFieldBase, self).__init__(*args, **kwargs)

        def to_python(self, value):
            if isinstance(value, str) and value:
                try:
                    return json.loads(value, **self.load_kwargs)
                except ValueError:
                    raise ValidationError(_("Enter valid JSON"))
            return value

        def clean(self, value):

            if not value and not self.required:
                return None

            # Trap cleaning errors & bubble them up as JSON errors
            try:
                return super(JSONFormFieldBase, self).clean(value)
            except TypeError:
                raise ValidationError(_("Enter valid JSON"))


    class JSONFormField(JSONFormFieldBase, fields.CharField):
        pass


    class JSONCharFormField(JSONFormFieldBase, fields.CharField):
        pass


    class JSONField(JSONFieldBase, models.TextField):
        """JSONField is a generic textfield that serializes/deserializes JSON objects"""
        form_class = JSONFormField

        def dumps_for_display(self, value):
            kwargs = {"indent": 2}
            kwargs.update(self.dump_kwargs)
            return json.dumps(value, ensure_ascii=False, **kwargs)


    class JSONCharField(JSONFieldBase, models.CharField):
        """JSONCharField is a generic textfield that serializes/deserializes JSON objects,
        stored in the database like a CharField, which enables it to be used
        e.g. in unique keys"""
        form_class = JSONCharFormField


    try:
        from south.modelsinspector import add_introspection_rules
        add_introspection_rules([], ["^jsonfield\.fields\.(JSONField|JSONCharField)"])
    except ImportError:
        pass

__all__ = ['JSONField']