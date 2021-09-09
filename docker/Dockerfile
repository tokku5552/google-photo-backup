FROM centos:7

WORKDIR /google-photo-backup

# system update
RUN yum -y update && yum clean all
RUN yum -y update && \
    yum -y groupinstall "Development Tools"

# set locale
RUN yum reinstall -y glibc-common && yum clean all
ENV LANG ja_JP.UTF-8

# editor install
RUN yum install -y vim && yum clean all

# python env install
RUN yum install -y https://repo.ius.io/ius-release-el7.rpm
RUN yum install -y python36u python36u-libs python36u-devel python36u-pip
RUN pip3 install google-auth google_auth_oauthlib google-api-python-client python-dateutil