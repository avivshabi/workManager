def compute(buffer, iterations):
    import hashlib
    output = hashlib.sha512(buffer).digest()

    for i in range(iterations - 1):
        output = hashlib.sha512(output).digest()

    return output
