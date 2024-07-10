@ECHO OFF

REM Minimal makefile for Sphinx documentation
REM

REM You can set these variables from the command line.
set SPHINXOPTS=
set SPHINXBUILD=sphinx-build
set SPHINXPROJ=Plurals
set SOURCEDIR=.
set BUILDDIR=_build

if "%1" == "" (
    %SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
) else (
    %SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
)
