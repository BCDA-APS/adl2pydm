# pydm installed with bluesky

Noticing that *designer* is not working with (at least one of) my
*bluesky* installations, I want to identify why.

## Environment variables

Per the revised [installation notes](install-pydm.md), designer
works (*works* means: finds the PyDM widget plugins)
when *pydm* is installed in a custom conda environment.

In my typical *bluesky* environment, designer does not find the plugins.
A comparison of the environment variables for each is obtained
with the command `env | sort > ${CONDA_DEFAULT_ENV}.txt`
The [differences](diffs.txt) between the two environments are minor.
Both `EPICS_BASE` and `EPICS_HOST_ARCH` are not relevant.
`PYQTDESIGNERPATH` is defined properly (and populated properly) in both.
For the *bluesky* environment, `PATH` has an extra (and unnecessary)
`/home/mintadmin/Apps/anaconda/bin` as the second item, but removing this
from `PATH` has no effect.

It's not obvious why, when using the *bluesky* environment, the designer
does not find the PyDM widget plugins.  However, examination of the environment
variables does not reveal the reason.

## Installed packages

For each environment, make a list of the packages with:

    conda list > /tmp/list-${CONDA_DEFAULT_ENV}.txt

Then compare the two files with linux `diff` command:

    diff /tmp/list-bluesky.txt /tmp/list-pydm-only.txt

The `diff` tool does not handle this well.  For example,
`pyqt` is in both environments but on vastly difference line
numbers such that they are not compared directly.


## Installation PyDM + Bluesky

Easier to set up a *new* conda environment
with the packages we want than to decide what are the
important differences between the existing bluesky and
pydm-only environments (the `diff` command).

Here are bash commands to make the new environment.

```
# name the custom environment
ENVO=bluesky-pydm

# build ${ENVO} environment
PACKAGES="pydm"
PACKAGES="${PACKAGES} bluesky ophyd databroker hklpy hkl"
PACKAGES="${PACKAGES} apstools stdlogpj pyRestTable spec2nexus pvview bcdamenu"
PACKAGES="${PACKAGES} ipython jupyter notebook jupyterlab flask"
PACKAGES="${PACKAGES} anaconda-client anaconda-project"
PACKAGES="${PACKAGES} sphinx sphinx_rtd_theme"
PACKAGES="${PACKAGES} pytest twine coverage coveralls versioneer"
PACKAGES="${PACKAGES} cfunits curl blosc"
CHANNELS="-c conda-forge -c nsls2forge -c aps-anl-tag"

conda create -y -n ${ENVO} python ${PACKAGES} ${CHANNELS}
conda activate ${ENVO}
```

Test the new environment using these commands:

```
# launch applications
designer /tmp/uptime.ui
pydm  --hide-nav-bar --hide-menu-bar --hide-status-bar /tmp/uptime.ui
```

Note: the file `uptime.ui` has a single
[PyDMLabel](https://slaclab.github.io/pydm/widgets/label.html)
widget that displays the value of `xxx:UPTIME`.
Create this file for yourself
with *designer* and use any PV of your choice.
