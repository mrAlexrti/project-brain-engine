from importlib.metadata import entry_points


def test_application_and_cli_entry_points_load() -> None:
    from brain_engine.application import create_app
    from brain_engine.application.services.brain_service import BrainService
    import brain_engine.cli as cli

    assert BrainService
    assert create_app
    assert cli.app
    brain_entry = next(
        entry for entry in entry_points(group="console_scripts") if entry.name == "brain"
    )
    assert brain_entry.load() is cli.app
