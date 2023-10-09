[![](https://img.shields.io/pypi/v/foliantcontrib.escapecode.svg)](https://pypi.org/project/foliantcontrib.escapecode/) [![](https://img.shields.io/github/v/tag/foliant-docs/foliantcontrib.escapecode.svg?label=GitHub)](https://github.com/foliant-docs/foliantcontrib.escapecode)

# EscapeCode and UnescapeCode

EscapeCode and UnescapeCode preprocessors work in pair.

EscapeCode finds in the source Markdown content the parts that should not be modified by any next preprocessors. Examples of content that should be left raw: fence code blocks, pre code blocks, inline code.

EscapeCode replaces these raw content parts with pseudo-XML tags recognized by UnescapeCode preprocessor.

EscapeCode saves raw content parts into files. Later, UnescapeCode restores this content from files.

Also, before the replacement, EscapeCode normalizes the source Markdown content to unify and simplify further operations. The preprocessor replaces `CRLF` with `LF`, removes excessive whitespace characters, provides trailing newline, etc.

## Installation

To install EscapeCode and UnescapeCode preprocessors, run:

```bash
$ pip install foliantcontrib.escapecode
```

See more details below.

## Integration with Foliant and Includes

You may call EscapeCode and UnescapeCode explicitly, but these preprocessors are integrated with Foliant core (since version 1.0.10) and with Includes preprocessor (since version 1.1.1).

The `escape_code` project’s config option, if set to `true`, provides applying EscapeCode before all other preprocessors, and applying UnescapeCode after all other preprocessors. Also this option tells Includes preprocessor to apply EscapeCode to each included file.

In this mode EscapeCode and UnescapeCode preprocessors deprecate _unescape preprocessor.

    >    **Note**
    >
    >    The preprocessor _unescape is a part of Foliant core. It allows to use pseudo-XML tags in code examples. If you want an opening tag not to be interpreted by any preprocessor, precede this tag with the `<` character. The preprocessor _unescape applies after all other preprocessors and removes such characters.

Config example:

```yaml
title: My Awesome Project

chapters:
    - index.md
    ...

escape_code: true

preprocessors:
    ...
    - includes
    ...
...
```

If the `escape_code` option isn’t used or set to `false`, backward compatibility mode is involved. In this mode EscapeCode and UnescapeCode aren’t applied automatically, but _unescape preprocessor is applied.

In more complicated case, you may pass some custom options to EscapeCode preprocessor:

```
escape_code:
    options:
        ...
```

Custom options available in EscapeCode since version 1.0.2. Foliant core supports passing custom options to EscapeCode preprocessor as the value of `escape_code.options` parameter since version 1.0.11. Options are described below.

The Python package that includes EscapeCode and UnescapeCode preprocessors is the dependence of Includes preprocessor since version 1.1.1. At the same time this package isn’t a dependence of Foliant core. To use `escape_code` config option in Foliant core, you have to install the package with EscapeCode and UnescapeCode preprocessors separately.

## Explicit Enabling

You may not want to use the `escape_code` option and call the preprocessors explicitly:

```yaml
preprocessors:
    - escapecode      # usually the first list item
    ...
    - unescapecode    # usually the last list item
```

Both preprocessors allow to override the path to the directory that is used to store temporary files:

```yaml
preprocessors:
    - escapecode:
        cache_dir: !path .escapecodecache
    ...
    - unescapecode:
        cache_dir: !path .escapecodecache
```

The default values are shown in this example. EscapeCode and related UnescapeCode must work with the same cache directory.

Note that if you use Includes preprocessor, and the included content doesn’t belong to the current Foliant project, there’s no way to escape raw parts of this content before Includes preprocessor is applied.

## Config

Since version 1.0.2, EscapeCode preprocessor supports the option `actions` in additional to `cache_dir`.

The value of `actions` options should be a list of acceptable actions. By default, the following list is used:

```yaml
actions:
    - normalize
    - escape:
        - fence_blocks
        - pre_blocks
        - inline_code
```

This default list may be overridden. For example:

```yaml
actions:
    - normalize
    - escape:
        - fence_blocks
        - inline_code
        - tags:
            - plantuml
            - seqdiag
        - comments
    - pattern_override:
        inline_code: '\<pattern_override_inline_code_\d+\>'
```

Meanings of parameters:

* `normalize`—perform normalization;
* `escape`—perform escaping of certain types of raw content:
    * `fence_blocks`—fence code blocks;
    * `pre_blocks`—pre code blocks;
    * `inline_code`—inline code;
    * `comments`—HTML-style comments, also usual for Markdown;
    * `tags`—content of certain tags with the tags themselves, for example `plantuml` for `<plantuml>...</plantuml>`;
    * `frontmatter`—the part with metadata at the beginning of the Markdown file, supports YAML `---` and TOML `+++` formats.
* `pattern_override`—a regular expression that will not be escaped:
    * `pre_blocks`—the lines of the pre code block containing this template will not be escaped;
    * `inline_code`—pattern for inline code;
    * `comments`—pattern for HTML-style comments, also usual for Markdown.

## Usage

Below you can see an example of Markdown content with code blocks and inline code.

    # Heading

    Text that contains some `inline code`. Text containing `<pattern_override_inline_code_01>`.

    Below is a fence code block, language is optional:

    ```python
    import this
    ```

    One more fence code block:

    ~~~
    # This is a comment that should not be interpreted as a heading

    print('Hello World')
    ~~~

    One more fence code block in list:

    - first list item

      ```python
      import this
      ```

    - second list item

    And this is a pre code block:

        mov dx, hello;
        mov ah, 9;
        int 21h;

The preprocessor EscapeCode with default behavior will do the following replacements:

    # Heading

    Text that contains some <<escaped hash="2bb20aeb00314e915ecfefd86d26f46a"></escaped>. Text containing `<pattern_override_inline_code_01>`.

    Below is a fence code block, language is optional:

    <<escaped hash="15e1e46a75ef29eb760f392bb2df4ebb"></escaped>

    One more fence code block:

    <<escaped hash="91c3d3da865e24c33c4b366760c99579"></escaped>

    One more fence code block in list:

    - first list item

      <<escaped hash="15e1e46a75ef29eb760f392bb2df4ebb"></escaped>

    - second list item

    And this is a pre code block:

        <<escaped hash="644952599350cd6676697cc95f52b999"></escaped>
        <<escaped hash="e24afa46b55281fcf0b4b0e38d10419c"></escaped>
        <<escaped hash="6bf655ac3a98b481ef3d33ac8dfcd93f"></escaped>

Escaped content parts will be saved into files located in the cache directory. The names of the files correspond the values of the `hash` attributes. For example, that’s the content of the file `15e1e46a75ef29eb760f392bb2df4ebb.md`:

    ```python
    import this
    ```
