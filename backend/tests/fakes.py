"""Shared fake Supabase client for unit tests. Not a test module itself."""


class FakeQuery:
    def __init__(self, execute_result, calls):
        self._execute_result = execute_result
        self._calls = calls

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self._calls.append((name, args, kwargs))
            return self

        return method

    def execute(self):
        self._calls.append(("execute", (), {}))
        if isinstance(self._execute_result, Exception):
            raise self._execute_result
        return self._execute_result


class FakeSupabaseClient:
    def __init__(self, execute_result):
        self.execute_result = execute_result
        self.calls = []

    def table(self, name):
        self.calls.append(("table", (name,), {}))
        return FakeQuery(self.execute_result, self.calls)
