```
      ___           ___       ___           ___           ___                   ___           ___     
     /\  \         /\__\     |\__\         /\  \         /\__\      ___        /\__\         /\  \    
    /::\  \       /:/  /     |:|  |       /::\  \       /:/  /     /\  \      /::|  |       /::\  \   
   /:/\ \  \     /:/  /      |:|  |      /:/\:\  \     /:/  /      \:\  \    /:|:|  |      /:/\:\  \  
  _\:\~\ \  \   /:/  /       |:|__|__   /::\~\:\__\   /:/  /       /::\__\  /:/|:|__|__   /::\~\:\  \ 
 /\ \:\ \ \__\ /:/__/        /::::\__\ /:/\:\ \:|__| /:/__/     __/:/\/__/ /:/ |::::\__\ /:/\:\ \:\__\
 \:\ \:\ \/__/ \:\  \       /:/~~/~    \:\~\:\/:/  / \:\  \    /\/:/  /    \/__/~~/:/  / \:\~\:\ \/__/
  \:\ \:\__\    \:\  \     /:/  /       \:\ \::/  /   \:\  \   \::/__/           /:/  /   \:\ \:\__\  
   \:\/:/  /     \:\  \    \/__/         \:\/:/  /     \:\  \   \:\__\          /:/  /     \:\ \/__/  
    \::/  /       \:\__\                  \::/__/       \:\__\   \/__/         /:/  /       \:\__\    
     \/__/         \/__/                   ~~            \/__/                 \/__/         \/__/    

```

[![ko-fi](https://www.ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/U7U11ZLB8)

Slyblime is Sylvester the Cat's Common Lisp IDE for **Sublime Text 4**:

Slyblime is an implementation of [SLY](https://github.com/joaotavora/sly) and uses the same backend (SLYNK).

Currently it includes:

* REPL integration including backtracking
* Autocomplete and documentation
* References, disassembly, macroexpansion etc.
* Inspection support
* Tracing support
* Compilation support with notes
* Multiple connexions
* Debugger including stack frame inspection
* **NEW!** Ability to open an inferior Lisp directly from the editor!

The primary missing feature is the ability to use stickers from Sly.


## Usage

### Using an inferior Lisp

Go to the settings and set the inferior lisp command to what you want (by default it's `lisp`).
After that run `Sly: Start and connect to an inferior Lisp instance` to start a inferior lisp and REPL.

### External connexion
To connect to a Slynk instance run `Sly: Connect to slynk` using the command palette.
Make sure to use the included `Lisp+` syntax for all the features to work correctly.

## Installation
First install [SublimeREPL](https://github.com/wuub/SublimeREPL).
Either download the file and unzip it in ST's packages folder or just use Package Control to install it.

## Copying

See [COPYING.md](COPYING.md)

## Contributing

Open an issue or a pull request.

