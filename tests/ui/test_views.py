# Copyright 2013 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

import textwrap

import pretend
import pytest

from werkzeug.exceptions import NotFound

from warehouse.packaging.models import Project
from warehouse.ui.views import project_detail


def test_project_detail_missing_project():
    app = pretend.stub(
        models=pretend.stub(
            packaging=pretend.stub(
                get_project=pretend.call_recorder(lambda proj: None),
            ),
        ),
    )
    request = pretend.stub()

    project_name = "test-project"

    with pytest.raises(NotFound):
        project_detail(app, request, project_name)

    assert app.models.packaging.get_project.calls == [
        pretend.call("test-project"),
    ]


def test_project_detail_no_versions():
    app = pretend.stub(
        models=pretend.stub(
            packaging=pretend.stub(
                get_project=pretend.call_recorder(
                    lambda proj: Project("test-project"),
                ),
                get_project_versions=pretend.call_recorder(lambda proj: []),
            ),
        ),
    )
    request = pretend.stub()

    project_name = "test-project"

    with pytest.raises(NotFound):
        project_detail(app, request, project_name)

    assert app.models.packaging.get_project.calls == [
        pretend.call("test-project"),
    ]
    assert app.models.packaging.get_project_versions.calls == [
        pretend.call("test-project"),
    ]


@pytest.mark.parametrize("fastly", [True, False])
def test_project_detail_redirects(fastly):
    app = pretend.stub(
        config=pretend.stub(
            cache=pretend.stub(
                browser=False,
                varnish=False,
            ),
            fastly=fastly,
        ),
        models=pretend.stub(
            packaging=pretend.stub(
                get_project=pretend.call_recorder(
                    lambda proj: Project("test-project"),
                ),
                get_project_versions=pretend.call_recorder(
                    lambda proj: ["1.0"],
                ),
            ),
        ),
    )
    request = pretend.stub(
        url_adapter=pretend.stub(
            build=pretend.call_recorder(
                lambda *a, **kw: "/projects/test-project/",
            ),
        ),
    )

    project_name = "test-Project"
    normalized = "test-project"

    resp = project_detail(app, request, project_name)

    assert resp.status_code == 301
    assert resp.headers["Location"] == "/projects/test-project/"

    if fastly:
        assert resp.headers["Surrogate-Key"] == \
            "project-detail project-detail~{}".format(normalized)
    else:
        assert "Surrogate-Key" not in resp.headers

    assert app.models.packaging.get_project.calls == [
        pretend.call("test-Project"),
    ]
    assert app.models.packaging.get_project_versions.calls == [
        pretend.call("test-project"),
    ]
    assert request.url_adapter.build.calls == [
        pretend.call(
            "warehouse.ui.views.project_detail",
            {"project_name": "test-project", "version": None},
            force_external=False,
        ),
    ]


def test_project_detail_invalid_version():
    app = pretend.stub(
        config=pretend.stub(
            cache=pretend.stub(
                browser=False,
                varnish=False,
            ),
        ),
        models=pretend.stub(
            packaging=pretend.stub(
                get_project=pretend.call_recorder(
                    lambda proj: Project("test-project"),
                ),
                get_project_versions=pretend.call_recorder(
                    lambda proj: ["1.0"],
                ),
            ),
        ),
    )
    request = pretend.stub()

    project_name = "test-project"

    with pytest.raises(NotFound):
        project_detail(app, request, project_name, "2.0")

    assert app.models.packaging.get_project.calls == [
        pretend.call("test-project"),
    ]
    assert app.models.packaging.get_project_versions.calls == [
        pretend.call("test-project"),
    ]


@pytest.mark.parametrize(("version", "description", "fastly"), [
    (
        None,
        textwrap.dedent("""
            Test Project
            ============

            This is a test project
        """),
        True,
    ),
    (
        None,
        textwrap.dedent("""
            Test Project
            ============

            This is a test project
        """),
        False,
    ),
    (
        "1.0",
        textwrap.dedent("""
            Test Project
            ============

            This is a test project
        """),
        True,
    ),
    (
        "1.0",
        textwrap.dedent("""
            Test Project
            ============

            This is a test project
        """),
        False,
    ),
    (None, ".. code-fail::\n    wat", True),
    (None, ".. code-fail::\n    wat", False),
    ("1.0", ".. code-fail::\n    wat", True),
    ("1.0", ".. code-fail::\n    wat", False),
])
def test_project_detail_valid(version, description, fastly):
    release = {
        "description": description,
    }

    template = pretend.stub(
        render=pretend.call_recorder(lambda **ctx: ""),
    )

    app = pretend.stub(
        config=pretend.stub(
            cache=pretend.stub(
                browser=False,
                varnish=False,
            ),
            fastly=fastly,
        ),
        models=pretend.stub(
            packaging=pretend.stub(
                get_project=pretend.call_recorder(
                    lambda proj: Project("test-project"),
                ),
                get_project_versions=pretend.call_recorder(
                    lambda proj: ["2.0", "1.0"],
                ),
                get_release=pretend.call_recorder(
                    lambda proj, version: release,
                ),
                get_releases=pretend.call_recorder(lambda proj: [release]),
                get_download_counts=pretend.call_recorder(
                    lambda proj: {
                        "last_day": 1,
                        "last_week": 7,
                        "last_month": 30,
                    },
                ),
                get_downloads=pretend.call_recorder(lambda proj, ver: []),
                get_classifiers=pretend.call_recorder(lambda proj, ver: []),
                get_documentation_url=pretend.call_recorder(
                    lambda proj: None,
                ),
                get_bugtrack_url=pretend.call_recorder(lambda proj: None),
            ),
        ),
        templates=pretend.stub(
            get_template=pretend.call_recorder(lambda t: template),
        ),
    )
    request = pretend.stub()

    project_name = "test-project"
    normalized = "test-project"

    resp = project_detail(app, request, project_name, version)

    assert resp.status_code == 200

    if fastly:
        assert resp.headers["Surrogate-Key"] == \
            "project-detail project-detail~{}".format(normalized)
    else:
        assert "Surrogate-Key" not in resp.headers

    assert app.models.packaging.get_project.calls == [
        pretend.call("test-project"),
    ]
    assert app.models.packaging.get_project_versions.calls == [
        pretend.call("test-project"),
    ]
