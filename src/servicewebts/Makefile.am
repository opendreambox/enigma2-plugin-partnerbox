AM_CPPFLAGS = \
	@PYTHON_CPPFLAGS@ \
	-include Python.h

AM_CXXFLAGS = \
	-Wall \
	-fno-exceptions \
	@ENIGMA2_CFLAGS@ \
	@PTHREAD_CFLAGS@

plugindir = $(libdir)/enigma2/python/Plugins/Extensions/Partnerbox

plugin_LTLIBRARIES = servicewebts.la

servicewebts_la_SOURCES = \
	servicewebts.cpp \
	servicewebts.h

servicewebts_la_LDFLAGS = \
	-avoid-version \
	-module \
	-shared
