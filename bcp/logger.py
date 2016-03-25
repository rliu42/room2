def log(s):
	out = open("log.txt", "a")
	out.write("\n" + str(s))
	out.close()


def clear():
	out = open("log.txt", "w")
	out.write("")
	out.close()

