import pytest

from mock import Mock

import threading
import time

from spalloc import Job, JobState, JobDestroyedError

from spalloc.job import JobStateTuple, JobMachineInfoTuple

from common import MockServer

GOOD_VERSION = "0.0.2"


@pytest.yield_fixture
def bg_version_connect(s):
    # Accept a connection, send back a compatible version and accept a job
    # creation request from a client.
    
    started = threading.Event()
    
    def connect_and_send_version():
        s.listen()
        started.set()
        s.connect()
        # Version response
        assert s.recv()["command"] == "version"
        s.send({"return": GOOD_VERSION})
        # Create job response
        assert s.recv()["command"] == "create_job"
        s.send({"return": 1})
    t = threading.Thread(target=connect_and_send_version)
    t.start()
    started.wait()
    
    yield t
    
    t.join()

@pytest.yield_fixture
def j(s, bg_version_connect):
    # Create a job and create/destroy it
    j = Job(hostname="localhost", owner="me")
    j.create()
    bg_version_connect.join()
    yield j
    s.send({"return": None})
    j.destroy()

@pytest.mark.parametrize("version,ok",
                         [(GOOD_VERSION, True),
                          ("0.0.2", True),
                          ("1.0.0", True),
                          ("01.001.0001", True),
                          ("2.0.0", False),
                          ("03.4.5", False)])
def test_create(s, no_config_files, version, ok):
    started = threading.Event()
    
    def connect_and_send_version():
        s.listen()
        started.set()
        s.connect()
        # Version response
        s.send({"return": version})
        if ok:
            # Create job response
            s.send({"return": 1})
            # Destroy job response
            s.send({"return": None})
    t = threading.Thread(target=connect_and_send_version)
    t.start()
    started.wait()
    
    j = Job(hostname="localhost", owner="me")
    if ok:
        # If a good version is supplied, should continue to register the job
        j.create()
        assert s.recv() == {"command": "version", "args": [], "kwargs": {}}
        assert s.recv() == {"command": "create_job",
                            "args": [],
                            "kwargs": {"owner": "me",
                                       "keepalive": 60.0,
                                       "machine": None,
                                       "tags": None,
                                       "min_ratio": 0.333,
                                       "max_dead_boards": 0,
                                       "max_dead_links": None,
                                       "require_torus": False}}
        j.destroy()
        assert s.recv() == {"command": "destroy_job",
                            "args": [1, None], "kwargs": {}}

    else:
        # If a bad version number is returned, should just stop
        with pytest.raises(ValueError):
            j.create()
        assert s.recv() == {"command": "version", "args": [], "kwargs": {}}
    
    t.join()

class TestKeepalive(object):

    @pytest.mark.timeout(1.0)
    def test_normal_operation(self, bg_version_connect, s, no_config_files):
        # Make sure that the keepalive is sent out at the correct interval by
        # the background thread.
        j = Job(hostname="localhost", owner="me",
                keepalive=0.2)
        last = time.time()
        j.create()
        bg_version_connect.join()
        
        try:
            for _ in range(3):
                # Wait for a keepalive to arrive
                assert s.recv() == {
                    "command": "job_keepalive", "args": [1], "kwargs": {}}
                s.send({"return": None})
                
                # Should have been at the correct interval
                now = time.time()
                assert 0.1 <= now - last < 0.2
                last = now
        finally:
            # Absorb any mistakes if this is failing
            for _ in range(10):
                s.send({"return": None})
            j.destroy()

    @pytest.mark.timeout(1.0)
    def test_reconnect(self, bg_version_connect, s, no_config_files):
        # Make sure that we can reconnect in the keepalive thread
        j = Job(hostname="localhost", owner="me",
                keepalive=0.2, reconnect_delay=0.2)
        j.create()
        bg_version_connect.join()
        
        # Now reconnect client
        s.close()
        s = MockServer()
        s.listen()
        s.connect()
        s.send({"return": GOOD_VERSION})
        assert s.recv()["command"] == "version"
        
        # Make sure keepalives keep coming
        try:
            for _ in range(3):
                # Wait for a keepalive to arrive
                assert s.recv() == {
                    "command": "job_keepalive", "args": [1], "kwargs": {}}
                s.send({"return": None})
        finally:
            # Absorb any mistakes if this is failing
            for _ in range(10):
                s.send({"return": None})
            j.destroy()
            s.close()

    @pytest.mark.timeout(1.0)
    def test_stop_while_server_down(self, bg_version_connect, s, no_config_files):
        # Make sure that we can stop the background thread while the server is
        # down.
        j = Job(hostname="localhost", owner="me",
                keepalive=0.2, reconnect_delay=0.2)
        j.create()
        bg_version_connect.join()
        
        # Disconnect client and make sure thread closes
        s.close()
        j.destroy()


@pytest.mark.timeout(1.0)
def test_get_state(bg_version_connect, s, j, no_config_files):
    s.send({"return": {"state": 3,
                       "power": True,
                       "keepalive": 60.0,
                       "reason": None}})
    assert j.get_state() == JobStateTuple(state=3, power=True,
                                          keepalive=60.0, reason=None)
    assert s.recv() == {"command": "get_job_state", "args": [1], "kwargs": {}}


@pytest.mark.timeout(1.0)
@pytest.mark.parametrize("power", [True, False])
def test_set_power(bg_version_connect, s, j, no_config_files, power):
    s.send({"return": None})
    j.set_power(power)
    assert s.recv() == {
        "command": "power_on_job_boards" if power else "power_off_job_boards",
        "args": [1], "kwargs": {}}


@pytest.mark.timeout(1.0)
def test_reset(bg_version_connect, s, j, no_config_files):
    s.send({"return": None})
    j.reset()
    assert s.recv() == {
        "command": "power_on_job_boards", "args": [1], "kwargs": {}}


@pytest.mark.timeout(1.0)
@pytest.mark.parametrize("allocated", [True, False])
def test_get_machine_info(bg_version_connect, s, j, no_config_files, allocated):
    if allocated:
        s.send({"return": {
            "width": 8, "height": 8,
            "connections": [((0, 0), "localhost")],
            "machine_name": "m",
        }})
    else:
        s.send({"return": {
            "width": None, "height": None,
            "connections": None, "machine_name": None,
        }})
    
    info = j.get_machine_info()
    assert s.recv() == {
        "command": "get_job_machine_info", "args": [1], "kwargs": {}}
    
    if allocated:
        assert info == JobMachineInfoTuple(
            width=8, height=8,
            connections={(0, 0): "localhost"},
            machine_name="m",
        )
    else:
        assert info == JobMachineInfoTuple(
            width=None, height=None,
            connections=None, machine_name=None,
        )

class TestWaitForStateChange(object):
    
    @pytest.mark.timeout(1.0)
    def test_state_already_changed(self, bg_version_connect, s, j, no_config_files):
        # If the state is already different to the state being watched, should
        # return straight away
        s.send({"return": None})
        s.send({"return": {"state": 3, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        assert j.wait_for_state_change(2) == 3
        
        assert s.recv()["command"] == "notify_job"
        assert s.recv()["command"] == "get_job_state"
    
    @pytest.mark.timeout(1.0)
    def test_change_on_event(self, bg_version_connect, s, j, no_config_files):
        # If the state change is notified via a notification, this should work.
        # We also send a "false-positive" change notification in this test.
        
        # notify_job
        s.send({"return": None})
        
        # get_job_state
        s.send({"return": {"state": 2, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        # job_keepalive prior to waiting
        s.send({"return": {}})
        
        # False positive and get_job_state
        s.send({"jobs_changed": [1]})
        s.send({"return": {"state": 2, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        # job_keepalive prior to waiting
        s.send({"return": {}})
        
        # True positive and get_job_state
        s.send({"jobs_changed": [1]})
        s.send({"return": {"state": 3, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        assert j.wait_for_state_change(2) == 3
        
        assert s.recv()["command"] == "notify_job"
        assert s.recv()["command"] == "get_job_state"
        assert s.recv()["command"] == "job_keepalive"
        assert s.recv()["command"] == "get_job_state"
        assert s.recv()["command"] == "job_keepalive"
        assert s.recv()["command"] == "get_job_state"
    
    @pytest.mark.timeout(1.0)
    @pytest.mark.parametrize("timeout", [None, 5.0])
    def test_keepalive(self, bg_version_connect, s, no_config_files, timeout):
        # Keepalives should be sent while waiting
        
        j = Job(hostname="localhost", owner="me", keepalive=0.2)
        # Don't let the background thread send any keepalives
        j._keepalive_thread = Mock()
        j.create()
        bg_version_connect.join()
        
        t = threading.Thread(target=j.wait_for_state_change,
                             args=[2], kwargs={"timeout": timeout})
        t.start()
        
        # notify_job
        assert s.recv()["command"] == "notify_job"
        s.send({"return": None})
        
        # get_job_state
        assert s.recv()["command"] == "get_job_state"
        s.send({"return": {"state": 2, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        # First keepalive
        assert s.recv()["command"] == "job_keepalive"
        s.send({"return": None})
        last = time.time()
        
        for _ in range(3):
            # job_keepalive should be sent at intervals of half the keepalive
            # time.
            assert s.recv()["command"] == "job_keepalive"
            s.send({"return": None})
            
            now = time.time()
            assert 0.1 <= now - last < 0.2
            last = now
            
        # Final keepalive
        assert s.recv()["command"] == "job_keepalive"
        s.send({"jobs_changed": [1]})
        s.send({"return": None})
        
        # Job now changed
        assert s.recv()["command"] == "get_job_state"
        s.send({"return": {"state": 3, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        t.join()
        
        # Return from the job being destroyed
        s.send({"return": None})
        j.destroy()
    
    @pytest.mark.timeout(1.0)
    def test_impossible_timeout(self, bg_version_connect, s, j, no_config_files):
        # When an impossible timeout is presented, should terminate immediately
        assert j.wait_for_state_change(2, timeout=0.0) == 2
    
    @pytest.mark.timeout(1.0)
    @pytest.mark.parametrize("keepalive", [None, 5.0])
    def test_timeout(self, bg_version_connect, s, no_config_files, keepalive):
        # Make sure that the timeout argument works when presented with a
        # no state-changes.
        
        j = Job(hostname="localhost", owner="me", keepalive=keepalive)
        # Don't let the background thread send any keepalives
        j._keepalive_thread = Mock()
        j.create()
        bg_version_connect.join()
        
        # notify_job
        s.send({"return": None})
        # get_job_state
        s.send({"return": {"state": 2, "power": True,
                           "keepalive": 60.0, "reason": None}})
        # job_keepalive
        s.send({"return": None})
        
        # Make sure timeout comes into effect
        before = time.time()
        assert j.wait_for_state_change(2, timeout=0.2) == 2
        after = time.time()
        assert 0.2 <= after - before < 0.3
        
        assert s.recv()["command"] == "notify_job"
        assert s.recv()["command"] == "get_job_state"
        assert s.recv()["command"] == "job_keepalive"
        
        # Return from the job being destroyed
        s.send({"return": None})
        j.destroy()
    
    @pytest.mark.timeout(1.0)
    def test_server_timeout(self, bg_version_connect, s, no_config_files):
        # Make sure that if the server dies, the timeout is still respected
        
        j = Job(hostname="localhost", owner="me")
        # Don't let the background thread send any keepalives
        j._keepalive_thread = Mock()
        j.create()
        bg_version_connect.join()
        
        # Kill the server and make sure we timeout eventually
        s.close()
        
        before = time.time()
        assert j.wait_for_state_change(2, timeout=0.2) == 2
        after = time.time()
        assert 0.2 <= after - before < 0.3
        
        j.destroy()
    
    @pytest.mark.timeout(1.0)
    def test_reconnect(self, bg_version_connect, s, no_config_files):
        # If the server disconnects, the client should reconnect
        
        # Don't wait too long to reconnect
        j = Job(hostname="localhost", owner="me", reconnect_delay=0.1)
        j.create()
        bg_version_connect.join()
        
        t = threading.Thread(target=j.wait_for_state_change, args=[2])
        t.start()
        
        # notify_job
        assert s.recv()["command"] == "notify_job"
        s.send({"return": None})
        
        # get_job_state
        assert s.recv()["command"] == "get_job_state"
        s.send({"return": {"state": 2, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        # First keepalive
        assert s.recv()["command"] == "job_keepalive"
        s.send({"return": None})
        
        # Server now disconnects...
        s.close()
        
        # Client should reconnect to a new server
        s = MockServer()
        s.listen()
        s.connect()
        assert s.recv()["command"] == "version"
        s.send({"return": GOOD_VERSION})
        
        # notify_job
        assert s.recv()["command"] == "notify_job"
        s.send({"return": None})
        
        # get_job_state, report a state change which should cause the wait to
        # end.
        assert s.recv()["command"] == "get_job_state"
        s.send({"return": {"state": 3, "power": True,
                           "keepalive": 60.0, "reason": None}})
        
        t.join()
        
        # Return from the job being destroyed
        s.send({"return": None})
        j.destroy()
        
        s.close()


class TestWaitUntilReady(object):
    
    @pytest.mark.timeout(1.0)
    def test_success(bg_version_connect, s, j, no_config_files):
        # Simple mocked implementation where at first the job is in the wrong
        # state then eventually in the correct state.
        j.get_state = Mock(side_effect=[
            JobStateTuple(state=JobState.power, power=True,
                          keepalive=60.0, reason=None)])
        j.wait_for_state_change = Mock(side_effect=[
            JobState.power, JobState.ready])
        
        j.wait_until_ready()
    
    @pytest.mark.timeout(1.0)
    @pytest.mark.parametrize("final_state",
                             [JobState.unknown, JobState.destroyed])
    @pytest.mark.parametrize("reason", ["dead", None])
    def test_bad_state(bg_version_connect, s, j, no_config_files,
                       final_state, reason):
        # Simple mocked implementation where the job enters an unrecoverable
        # state
        j.get_state = Mock(return_value=
            JobStateTuple(state=final_state, power=None,
                          keepalive=None, reason=reason))
        
        with pytest.raises(JobDestroyedError):
            j.wait_until_ready()
    
    @pytest.mark.timeout(1.0)
    def test_impossible_timeout(bg_version_connect, s, j, no_config_files):
        with pytest.raises(TimeoutError):
            j.wait_until_ready(timeout=0.0)
    
    @pytest.mark.timeout(1.0)
    def test_timeout(bg_version_connect, s, j, no_config_files):
        # Simple mocked implementation which times out
        j.get_state = Mock(return_value=
            JobStateTuple(state=JobState.power, power=True,
                          keepalive=60.0, reason=None))
        j.wait_for_state_change = Mock(
            side_effect=(lambda *a, **k: time.sleep(0.1)))
        
        before = time.time()
        with pytest.raises(TimeoutError):
            j.wait_until_ready(timeout=0.3)
        after = time.time()
        
        assert 0.3 <= after - before < 0.4
