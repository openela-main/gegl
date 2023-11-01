%if 0%{?rhel}
%bcond_with workshop
%else
%bcond_without workshop
%endif

# skip all tests
%global skip_all_checks 1
# skip tests known to be problematic in a specific version
%global skip_checks_version 0.2.0
# for some reason or other comparing generated to reference images segfaults in
# two test cases
# Well, now it is all of them, not just two. :/
%global skip_checks compositions/run-*.xml.sh

Summary:    A graph based image processing framework
Name:       gegl
Version:    0.2.0
Release:    39%{?dist}

# Compute some version related macros
# Ugly hack, you need to get your quoting backslashes/percent signs straight
%global major %(ver=%version; echo ${ver%%%%.*})
%global minor %(ver=%version; ver=${ver#%major.}; echo ${ver%%%%.*})
%global micro %(ver=%version; ver=${ver#%major.%minor.}; echo ${ver%%%%.*})
%global apiver %major.%minor

# The binary is under the GPL, while the libs are under LGPL
License:    LGPLv3+ and GPLv3+
URL:        http://www.gegl.org/
Source0:    http://download.gimp.org/pub/gegl/%{apiver}/%{name}-%{version}.tar.bz2
Patch0:     gegl-0.2.0-lua-5.2.patch
Patch1:     gegl-0.2.0-CVE-2012-4433.patch
Patch2:     gegl-0.2.0-remove-src-over-op.patch
Patch3:     0001-matting-levin-Fix-the-build-with-recent-suitesparse-.patch
Patch4:     gegl-0.2.0-linker-flags.patch
Patch5:     gegl-0.2.0-libopenraw.patch
Patch6:     gegl-0.2.0-ppc64-rand-fix.patch
Patch7:     gegl-build-without-exiv2.patch
BuildRequires:  asciidoc
BuildRequires:  babl-devel >= 0.1.10
BuildRequires:  cairo-devel
BuildRequires:  enscript
BuildRequires:  gdk-pixbuf2-devel >= 2.18.0
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  glib2-devel >= 2.28.0
BuildRequires:  graphviz
BuildRequires:  gtk2-devel >= 2.18.0
BuildRequires:  intltool >= 0.40.1
BuildRequires:  jasper-devel >= 1.900.1
%if %{with workshop}
BuildRequires:  lensfun-devel >= 0.2.5
%endif
BuildRequires:  libjpeg-devel
BuildRequires:  libopenraw-devel >= 0.0.5
BuildRequires:  libpng-devel
BuildRequires:  librsvg2-devel >= 2.14.0
BuildRequires:  libspiro-devel
BuildRequires:  libv4l-devel
BuildRequires:  lua-devel >= 5.1.0
BuildRequires:  OpenEXR-devel
BuildRequires:  pango-devel
BuildRequires:  perl-devel
BuildRequires:  pkgconfig
BuildRequires:  rubygems
BuildRequires:  SDL-devel
BuildRequires:  suitesparse-devel
Requires:       babl%{?_isa} >= 0.1.10
Requires:       dcraw

%description
GEGL (Generic Graphics Library) is a graph based image processing framework. 
GEGLs original design was made to scratch GIMPs itches for a new
compositing and processing core. This core is being designed to have
minimal dependencies. and a simple well defined API.

%if %{with workshop}
%package operations-workshop
Summary:    Experimental operations for GEGL
Requires:   %{name}%{_isa} = %{version}-%{release}

%description operations-workshop
This package contains experimental operations for GEGL. If used they may yield
unwanted results, or even crash. You're warned!
%endif

%package devel
Summary:    Headers for developing programs that will use %{name}
Requires:   %{name}%{_isa} = %{version}-%{release}
Requires:   pkgconfig
Requires:   babl-devel%{_isa}
Requires:   glib2-devel%{_isa}

%description devel
This package contains the libraries and header files needed for
developing with %{name}.

%prep
%autosetup -p1

%build
# use hardening compiler/linker flags because gegl is likely to deal with
# untrusted input
%global _hardened_build 1

# Needed by Ruby 1.9.3.
export LANG=en_US.utf8

%configure \
%if %{with workshop}
    --enable-workshop \
%else
    --disable-workshop \
%endif
    --with-pic \
    --with-gio \
    --with-gtk \
    --with-cairo \
    --with-pango \
    --with-pangocairo \
    --with-gdk-pixbuf \
    --with-lensfun \
    --with-libjpeg \
    --with-libpng \
    --with-librsvg \
    --with-openexr \
    --with-sdl \
    --with-libopenraw \
    --with-jasper \
    --with-graphviz \
    --with-lua \
    --without-libavformat \
    --with-libv4l \
    --with-libspiro \
    --with-exiv2 \
    --with-umfpack \
    --disable-static \
    --disable-gtk-doc \
    --disable-silent-rules

%make_build

%install
%make_install
pushd operations
# favor non-workshop binaries
make SUBDIRS= install INSTALL='install -p'
for d in */; do
    d="${d%/}"
    if [ "$d" != "workshop" ]; then
        pushd "$d"
        make DESTDIR=%{buildroot} install INSTALL='install -p'
        popd
    fi
done
popd

rm -f %{buildroot}%{_libdir}/*.la
rm -f %{buildroot}%{_libdir}/gegl-%{apiver}/*.la

# keep track of workshop/non-workshop operations
opsdir="$PWD/operations"

files_ws="$PWD/operations_files_workshop"
files_non_ws="$PWD/operations_files"
non_ws_filenames_file="$PWD/non_ws_filenames"

find "$opsdir" -path "$opsdir/workshop" -prune -o -regex '.*/\.libs/.*\.so' -printf '%f\n' > "$non_ws_filenames_file"

echo '%%defattr(-, root, root, -)' > "$files_non_ws"
echo '%%defattr(-, root, root, -)' > "$files_ws"

pushd %{buildroot}%{_libdir}/gegl-%{apiver}
for opfile in *.so; do
    if fgrep -q -x "$opfile" "$non_ws_filenames_file"; then
        echo "%{_libdir}/gegl-%{apiver}/$opfile" >> "$files_non_ws"
    else
        echo "%{_libdir}/gegl-%{apiver}/$opfile" >> "$files_ws"
    fi
done
popd

%find_lang %{name}-%{apiver}

%check
%if 0%{skip_all_checks} < 1
# skip tests known to be problematic in a specific version
%if "%version" == "%skip_checks_version"
pushd tests
for problematic in %skip_checks; do
    rm -f "$problematic"
    cat << EOF > "$problematic"
#!/bin/sh
echo Skipping test "$problematic"
EOF
    chmod +x "$problematic"
done
popd
%endif
make check
%endif

%ldconfig_scriptlets

%files -f operations_files -f %{name}-%{apiver}.lang
%doc AUTHORS ChangeLog COPYING COPYING.LESSER NEWS README
%{_bindir}/gegl
%{_libdir}/*.so.*
%dir %{_libdir}/gegl-%{apiver}/

%if %{with workshop}
%files operations-workshop -f operations_files_workshop
%endif

%files devel
%doc %{_datadir}/gtk-doc/
%{_includedir}/gegl-%{apiver}/
%{_libdir}/*.so
%{_libdir}/pkgconfig/%{name}-%{apiver}.pc

%changelog
* Mon Nov 04 2019 Jan Grulich <jgrulich@redhat.com> - 0.2.0-39
- Build without exiv2
  Resolves: bz#1767748

* Wed Feb 21 2018 Josef Ridky <jridky@redhat.com> - 0.2.0-38
- Remove Group tag from spec file

* Tue Feb 20 2018 Nils Philippsen <nils@tiptoe.de> - 0.2.0-37
- require gcc, gcc-c++ for building

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 0.2.0-36
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Sat Feb 03 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 0.2.0-35
- Switch to %%ldconfig_scriptlets

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.2.0-34
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.2.0-33
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.2.0-32
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Sun Dec 04 2016 Josef Ridky <jridky@redhat.com> - 0.2.0-31
- rebuild for jasper library

* Sat Dec 03 2016 Julian Sikorski <belegdol@fedoraproject.org> - 0.2.0-30
- Fixed building with libopenraw-0.1
- Added rubygems to BuildRequires to fix build error
- Modernised the .spec file a bit
- Disabled silent build

* Wed Apr 27 2016 Nils Philippsen <nils@redhat.com> - 0.2.0-29
- require dcraw (#1279143)

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 0.2.0-28
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Jan 19 2016 Nils Philippsen <nils@redhat.com>
- use %%global instead of %%define

* Sun Jan 03 2016 Rex Dieter <rdieter@fedoraproject.org> 0.2.0-27
- rebuild (lensfun)

* Wed Jun 24 2015 Rex Dieter <rdieter@fedoraproject.org> - 0.2.0-26
- rebuild (exiv2)

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-25
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Jun 11 2015 Nils Philippsen <nils@redhat.com> - 0.2.0-24
- rebuild for suitesparse-4.4.4

* Thu May 14 2015 Nils Philippsen <nils@redhat.com> - 0.2.0-23
- rebuild for lensfun-0.3.1

* Thu May 07 2015 Debarshi Ray <rishi@fedoraproject.org> - 0.2.0-22
- Add -lm to linker flags because of sqrt

* Thu Dec 04 2014 Kalev Lember <kalevlember@gmail.com> - 0.2.0-21
- Fix the build with recent suitesparse versions

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-20
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Tue Aug 05 2014 Nils Philippsen <nils@redhat.com> - 0.2.0-19
- update source URL

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-18
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri Dec 06 2013 Nils Philippsen <nils@redhat.com> - 0.2.0-17
- rebuild (suitesparse)

* Wed Dec 04 2013 Nils Philippsen <nils@redhat.com> - 0.2.0-16
- remove BR: w3m, it's only needed for "make dist"

* Tue Dec 03 2013 Rex Dieter <rdieter@fedoraproject.org> - 0.2.0-15
- rebuild (exiv2)

* Wed Nov 27 2013 Rex Dieter <rdieter@fedoraproject.org> - 0.2.0-14
- rebuild (openexr)

* Thu Sep 12 2013 Kalev Lember <kalevlember@gmail.com> - 0.2.0-13
- Rebuilt for ilmbase soname bump

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-12
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Mon Jul 01 2013 Nils Philippsen <nils@redhat.com> - 0.2.0-11
- replace lua-5.2 patch by upstream commit
- fix buffer overflow in and add plausibility checks to ppm-load op
  (CVE-2012-4433)
- fix multi-lib issue in generated documentation

* Wed May 15 2013 Tom Callaway <spot@fedoraproject.org> - 0.2.0-10
- rebuild for lua 5.2
- disable check suite (so broken)

* Sun Mar 10 2013 Rex Dieter <rdieter@fedoraproject.org> - 0.2.0-9
- rebuild (OpenEXR)

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Fri Jan 18 2013 Adam Tkac <atkac redhat com> - 0.2.0-7
- rebuild due to "jpeg8-ABI" feature drop

* Fri Dec 21 2012 Adam Tkac <atkac redhat com> - 0.2.0-6
- rebuild against new libjpeg

* Fri Oct 19 2012 Nils Philippsen <nils@redhat.com> - 0.2.0-5
- don't catch "make check" errors but skip known problematic tests

* Fri Oct 19 2012 Nils Philippsen <nils@redhat.com> - 0.2.0-4
- don't require lensfun-devel for building without workshop ops

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Wed May 02 2012 Rex Dieter <rdieter@fedoraproject.org> - 0.2.0-2
- rebuild (exiv2)

* Tue Apr 03 2012 Nils Philippsen <nils@redhat.com> - 0.2.0-1
- version 0.2.0
- split off workshop (i.e. experimental) operations
- don't build/package workshop operations on EL

* Mon Feb 06 2012 Vít Ondruch <vondruch@redhat.com> - 0.1.8-3
- Rebuilt for Ruby 1.9.3.

* Tue Jan 10 2012 Nils Philippsen <nils@redhat.com> - 0.1.8-2
- rebuild for gcc 4.7

* Tue Dec 13 2011 Nils Philippsen <nils@redhat.com> - 0.1.8-1
- version 0.1.8
- drop all patches
- add BRs: gdk-pixbuf2-devel, lensfun-devel
- update BR version: glib2-devel
- use %%_hardened_build macro instead of supplying our own hardening flags

* Thu Nov 17 2011 Nils Philippsen <nils@redhat.com> - 0.1.6-5
- don't require gtk-doc (#707554)

* Mon Nov 07 2011 Nils Philippsen <nils@redhat.com> - 0.1.6-4
- rebuild (libpng)

* Fri Oct 14 2011 Rex Dieter <rdieter@fedoraproject.org> - 0.1.6-3
- rebuild (exiv2)

* Wed Apr 06 2011 Nils Philippsen <nils@redhat.com> - 0.1.6-2
- fix crash when using hstack operation (#661533)

* Tue Feb 22 2011 Nils Philippsen <nils@redhat.com> - 0.1.6-1
- version 0.1.6
- remove obsolete patches
- fix erroneous use of destdir
- correct source URL
- add BR: exiv2-devel, jasper-devel, suitesparse-devel
- update BR versions
- update --with-*/--without-* configure flags
- replace tabs with spaces for consistency

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.1.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Oct 19 2010 Nils Philippsen <nils@redhat.com> - 0.1.2-4
- don't leak "root" symbol which clashes with (equally broken) xvnkb input
  method (#642992)

* Wed Jun 23 2010 Nils Philippsen <nils@redhat.com> - 0.1.2-3
- build with -fno-strict-aliasing
- use PIC/PIE because gegl is likely to deal with data coming from untrusted
  sources

* Fri Feb 26 2010 Nils Philippsen <nils@redhat.com>
- use tabs consistently
- let devel depend on gtk-doc

* Fri Feb 19 2010 Nils Philippsen <nils@redhat.com> - 0.1.2-2
- ignore make check failures for now

* Wed Feb 17 2010 Nils Philippsen <nils@redhat.com>
- avoid buffer overflow in gegl_buffer_header_init()
- correct gegl library version, use macro for it

* Tue Feb 16 2010 Nils Philippsen <nils@redhat.com> - 0.1.2-1
- version 0.1.2
- remove obsolete cflags, babl-instrumentation, autoreconf patches
- backported: don't leak each node set on a GeglProcessor

* Sat Jan 23 2010 Deji Akingunola <dakingun@gmail.com> - 0.1.0-3
- Rebuild for babl-0.1.2
- Backport upstream patch that removed babl processing time instrumentation

* Wed Jan 20 2010 Nils Philippsen <nils@redhat.com>
- use tabs consistently to appease rpmdiff

* Tue Aug 18 2009 Nils Philippsen <nils@redhat.com>
- explain patches

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.1.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Jul 02 2009 Nils Philippsen - 0.1.0-1
- fix cflags for building

* Thu Jul 02 2009 Nils Philippsen
- version 0.1.0
- use "--disable-gtk-doc" to avoid rebuilding documentation (#481404)
- remove *.la files in %%{_libdir}/gegl-*/ (#509292)

* Thu Jun 04 2009 Deji Akingunola <dakingun@gmail.com> - 0.0.22-5
- Apply patch to build with babl-0.1.0 API changes

* Thu Jun 04 2009 Nils Philippsen - 0.0.22-4
- rebuild against babl-0.1.0

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.0.22-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Thu Jan 29 2009 Nils Philippsen - 0.0.22-2
- use the same timestamps for certain documentation files on all architectures
  to avoid multi-lib conflicts (#481404)
- consolidate spec files between OS releases
- reenable building documentation on ppc64
- explicitly list more build requirements and/or versions to catch eventual
  problems during future builds

* Tue Jan 13 2009 Deji Akingunola <dakingun@gmail.com> - 0.0.22-1
- Update to version 0.0.22

* Tue Oct 07 2008 Deji Akingunola <dakingun@gmail.com> - 0.0.20-1
- Update to latest release

* Thu Jul 10 2008 Deji Akingunola <dakingun@gmail.com> - 0.0.18-1
- Update to latest release

* Thu Feb 28 2008 Deji Akingunola <dakingun@gmail.com> - 0.0.16-1
- New release

* Thu Jan 17 2008 Deji Akingunola <dakingun@gmail.com> - 0.0.15-1.svn20080117
- Update to a svn snapshot for gnome-scan
- Apply patch to fix extensions loading on 64bit systems
- Building the docs on ppc64 segfaults, avoid it for now.

* Sat Dec 08 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.14-1
- Update to 0.0.14 release
- License change from GPLv2+ to GPLv3+

* Thu Oct 25 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.7.20071011svn
- Include missing requires for the devel subpackage

* Thu Oct 25 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.6.20071011svn
- BR graphiz instead of graphiz-devel
- Remove the spurious exec flag from a couple of source codes

* Tue Oct 23 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.5.20071011svn
- Fix missing directory ownership

* Mon Oct 22 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.4.20071011svn
- Update the License field 

* Fri Oct 12 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.3.20071011svn
- Package the extension libraries in the main package
- Run 'make check'

* Fri Oct 12 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.2.20071011svn
- Remove the use of inexistent source

* Thu Oct 11 2007 Deji Akingunola <dakingun@gmail.com> - 0.0.13-0.1.20071011svn
- Initial packaging for Fedora
