"""   Tests for the module "acqsession2bids.py"   """

import sys

import pytest

from bidsphysio.session import session2bids
from bidsphysio.acq2bids import acqsession2bids

MOCK_MESSAGE = 'mock_convert_session called'


###   Fixtures   ###

@pytest.fixture
def mock_conversion(monkeypatch):
    """
    Pretend we run session2bids.convert_session, but do nothing
    This allows us to test the correct behavior of the runner without
       actually running anything: just the instructions in the runner
       before the call to session2bids.convert_session
    """

    def mock_convert_session(*args, **kwargs):
        print(MOCK_MESSAGE)
        pass

    monkeypatch.setattr(session2bids, "convert_session", mock_convert_session)


###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_conversion,
        capfd
):
    """ Tests for "main"
    Just check the arguments, etc.
    """
    # TODO: write a function to run the tests that are almost the same
    # 1) "infolder" doesn't exist:
    infolder = str(tmpdir / 'boo')
    bidsfolder = str(tmpdir / 'mybidsdir')
    args = (
        'acqsession2bids -i {infolder} -b {bf} -s {sub} --overwrite'.format(
            infolder=infolder,
            bf=bidsfolder,
            sub='01'
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(NotADirectoryError) as e_info:
        acqsession2bids.main()
    assert str(e_info.value).endswith(' folder not found')
    assert str(e_info.value).split(' folder not found')[0] == infolder

    # 2) "infolder" does exist, but output directory doesn't exist:
    args[args.index('-i') + 1] = str(tmpdir)
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(NotADirectoryError) as e_info:
        acqsession2bids.main()
    assert str(e_info.value).endswith(' folder not found')
    assert str(e_info.value).split(' folder not found')[0] == bidsfolder

    # 3) both "infolder" and "bidsfolder" exist:
    args[args.index('-b') + 1] = str(tmpdir)
    monkeypatch.setattr(sys, 'argv', args)
    acqsession2bids.main()

    # make sure we are not calling the mock_dcm2bidds, but the real one:
    assert capfd.readouterr().out == MOCK_MESSAGE + '\n'
