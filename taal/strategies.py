from __future__ import absolute_import

from sqlalchemy.sql.expression import and_, or_

from taal.translatablestring import TranslatableString


class Strategy(object):

    def __init__(self, language, model, session):
        self.language = language
        self.model = model
        self.session = session

    def translate(self, translatable):
        try:
            return self.cache[(translatable.context, translatable.message_id)]
        except KeyError:
            return self.translation_missing(translatable)

    def translation_missing(self, translatable):
        raise NotImplementedError

    def recursive_translate(self, translatable):
        self.cache = self._prepare_cache(translatable)

        if isinstance(translatable, TranslatableString):
            return self.translate(translatable)
        elif isinstance(translatable, dict):
            return dict(
                (key, self.recursive_translate(val))
                for key, val in translatable.iteritems()
            )
        elif isinstance(translatable, list):
            return [self.recursive_translate(item) for item in translatable]
        elif isinstance(translatable, tuple):
            return tuple(self.recursive_translate(item)
                         for item in translatable)
        else:
            return translatable

    def _prepare_cache(self, translatable):
        """
        Bulk load translations required to translate a translatable
        'structure'
        """
        translatable_pks = self._collect_translatables(translatable)
        if not translatable_pks:
            return {}

        pk_filter = or_(*(
            and_(
                self.model.context == context,
                self.model.message_id == message_id,
            )
            for context, message_id in translatable_pks
        ))

        translations = self.session.query(self.model).filter(
            self.model.language == self.language).filter(pk_filter).values(
            self.model.context, self.model.message_id, self.model.value)
        cache = {(t[0], t[1]): t[2] for t in translations}

        return cache

    def _collect_translatables(self, translatable, collection=None):
        """
        Run over a translatable 'structure' and collect the set of
        translatable primary keys (context and message_id tuples)
        These are then bulk loaded from the db
        """

        if collection is None:
            collection = set()

        if isinstance(translatable, TranslatableString):
            collection.add((translatable.context, translatable.message_id))
        elif isinstance(translatable, dict):
            [self._collect_translatables(val, collection)
                for val in translatable.itervalues()]
        elif isinstance(translatable, list):
            [self._collect_translatables(item, collection)
                for item in translatable]
        elif isinstance(translatable, tuple):
            [self._collect_translatables(item, collection)
                for item in translatable]

        return collection


class NoneStrategy(Strategy):

    def translation_missing(self, translatable):
        return None


class SentinelStrategy(Strategy):

    TRANSLATION_MISSING = "<TranslationMissing sentinel>"

    def translation_missing(self, translatable):
        return self.TRANSLATION_MISSING


class DebugStrategy(Strategy):

    def get_debug_translation(self, translatable):
        return u"[Translation missing ({}, {}, {})]".format(
            self.language, translatable.context, translatable.message_id)

    def translation_missing(self, translatable):
        return self.get_debug_translation(translatable)
