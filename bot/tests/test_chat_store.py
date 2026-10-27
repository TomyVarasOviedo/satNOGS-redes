from chat_store import ChatStore, read_chat_id, write_chat_id


def test_reads_and_writes_a_plain_text_file(tmp_path):
    path = tmp_path / "chat_id.txt"

    write_chat_id(path, -100123456)

    assert path.read_text(encoding="utf-8").strip() == "-100123456"
    assert read_chat_id(path) == -100123456


def test_env_chat_id_locks_the_store(tmp_path):
    path = tmp_path / "chat_id.txt"
    write_chat_id(path, 111)
    store = ChatStore(path, env_chat_id=222)

    assert store.chat_id == 222
    assert store.locked
    assert store.remember(333) is False
    assert store.chat_id == 222
    assert read_chat_id(path) == 111


def test_the_last_chat_wins_without_env(tmp_path):
    path = tmp_path / "chat_id.txt"
    store = ChatStore(path)

    assert store.chat_id is None
    assert store.remember(111) is True
    assert read_chat_id(path) == 111

    assert store.remember(222) is True
    assert read_chat_id(path) == 222
    assert ChatStore(path).chat_id == 222


def test_remembering_the_same_chat_does_not_rewrite(tmp_path):
    path = tmp_path / "chat_id.txt"
    store = ChatStore(path)
    store.remember(111)

    assert store.remember(111) is False


def test_a_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "chat_id.txt"
    path.write_text("not a number", encoding="utf-8")

    store = ChatStore(path)

    assert store.chat_id is None
    assert store.remember(111) is True
    assert read_chat_id(path) == 111
