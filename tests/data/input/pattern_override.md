# Test

## Inline code

Lorem ipsum `inline code` dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation `$var = 0` ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla `func(start, end)` pariatur. Excepteur sint occaecat cupidatat non
proident, sunt in culpa qui officia `<pattern_override_inline_code_01>` deserunt mollit anim id est laborum.

## Fence block code

```python
def fibonacci(max):
    a, b = 0, 1
    while a < max:
        yield a
        a, b = b, a + b

for n in fibonacci(100):
    print(n)
```

```python
def pattern_override_fence_block_code_02(max):
    a, b = 0, 1
    while a < max:
        yield a
        a, b = b, a + b

for n in fibonacci(100):
    print(n)
```

## Pre block code

    def fibonacci(max):
        a, b = 0, 1
        while a < max:
            yield a
            a, b = b, a + b

    for n in fibonacci(100):
        print(n)

    def pattern_override_pre_block_code_03(max):
        a, b = 0, 1
        while a < max:
            yield a
            a, b = b, a + b

    for n in fibonacci(100):
        print(n)

## Comments

<!-- test of comments -->

<!-- pattern_override_comments-04 -->
