class TranslatableString(object):
    def __init__(self, context, message_id):
        self.context = context
        self.message_id = message_id

    def __repr__(self):
        return "<TranslatableString: ({}, {})>".format(
            self.context, self.message_id)


class Translator(object):
    def __init__(self, model, session):
        self.model = model
        self.session = session

    def _translate(self, translatable, language):
        context = translatable.context
        message_id = translatable.message_id

        context_col = getattr(self.model, 'context')
        message_id_col = getattr(self.model, 'message_id')
        language_col = getattr(self.model, 'language')
        translation = self.session.query(self.model).filter(
            context_col == context,
            message_id_col == message_id,
            language_col == language
        ).one()

        return translation.translation

    def translate(self, translatable, language):
        if isinstance(translatable, TranslatableString):
            return self._translate(translatable, language)
        elif isinstance(translatable, dict):
            return dict(
                (key, self.translate(val, language))
                for key, val in translatable.iteritems()
            )
        elif isinstance(translatable, list):
            return list(
                self.translate(item, language)
                for item in translatable)

        else:
            return translatable


class TranslationContextManager(object):
    """ Knows all available ``message_id``s for a given context """

    context = None

    def list_message_ids(self):
        raise NotImplementedError()


class TranslationManager(object):
    """ Collection of ``TranslationContextManager``s """

    def __init__(self):
        self._registry = {}

    def register(self, context_manager):
        context = context_manager.context
        if context in self._registry:
            raise KeyError(
                "ContextManager with context '{}' already registered".format(
                context)
            )
        self._registry[context] = context_manager

    def list_contexts_and_message_ids(self, **kwargs):
        for context, context_manager_cls in self._registry.iteritems():
            context_manager = context_manager_cls(**kwargs)
            for message_id in context_manager.list_message_ids():
                yield (context, message_id)


translation_manager = TranslationManager()
