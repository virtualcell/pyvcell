import process_bigraph as pbg
import bigraph_schema as bgs
from typing import Any, Self, Generic, TypeVar

T = TypeVar('T')

class RegistrationMethods:

    @staticmethod
    def check_function() -> bool:
        raise NotImplementedError()

    @staticmethod
    def apply_function() -> T:
        raise NotImplementedError()

    @staticmethod
    def serialize_function() -> dict[str, Any]:
        raise NotImplementedError()

    @staticmethod
    def deserialize_function(value: dict[str, Any]) -> T:
        raise NotImplementedError()

    @staticmethod
    def divide_function():
        raise NotImplementedError()

    @staticmethod
    def construct_new_object() -> T:
        raise NotImplementedError()


    @classmethod
    def register_self(cls, core: bgs.Core, *args: Any, **kwargs: Any) -> None:
        pass
        # core.type_registry.apply_registry.register('apply_particle', apply_particle)
        # core.type_registry.check_registry.register('check_particle', check_particle)
        # core.type_registry.serialize_registry.register('serialize_particle', serialize_particle)
        # core.type_registry.deserialize_registry.register('deserialize_particle', deserialize_particle)
        # core.type_registry.divide_registry.register('divide_particle', divide_particle)
        #
        # core.type_registry.register('particle', {
        #     '_type': 'particle',
        #     '_apply': 'apply_particle',
        #     '_check': 'check_particle',
        #     '_serialize': 'serialize_particle',
        #     '_deserialize': 'deserialize_particle',
        #     '_divide': 'divide_particle',
        #     '_default': T(args=args, kwargs=kwargs),
        # })