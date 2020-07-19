# 1.0.3

-   Do not fail the preprocessor if saved code is not found, show warning message instead.

# 1.0.2

-   Improve flexibility: add new actions, allow to override defaults.

# 1.0.1

-   Do not ignore diagram definitions. It should be possible to escape the tags used by diagram drawing preprocessors. If some preprocessors need to work with the content that is recognized as code, call UnescapeCode explicitly before them.
