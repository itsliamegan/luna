def words(name: str) -> list[str]:
	return [word for word in name.split("_") if word]


def sentence(name: str) -> str:
	text = " ".join(words(name))
	return text[:1].upper() + text[1:]


def dash(name: str) -> str:
	return "-".join(words(name))
