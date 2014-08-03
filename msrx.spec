%define name    msrx
%define version 0.1
%define release 1

Name:           %{name}
Version:        %{version}
Release:        %{release}
Summary:        MSR605 library and command line tools

Group:          Development/Libraries
License:        GPLv3
Source0:        %{name}-%{version}.tar.gz
Vendor:         Mansour Behabadi <mansour@oxplot.com>
URL:            https://github.com/oxplot/msrx

BuildArch:      noarch
BuildRequires:  python >= 2.7
Requires:       python >= 2.7

%description
Library and command line tools for talking with MSR605 magnetic card
reader/writer.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%doc README.md LICENSE.txt

%changelog
* Fri Aug 3 2014 Mansour Behabadi <mansour@oxplot.com> - 0.1-1
- Initial release
