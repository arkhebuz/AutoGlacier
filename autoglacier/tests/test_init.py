import pytest
#~ import autoglacier

class TestInitialization(object):
    def test_ag_import(self):
        try: 
            import autoglacier.ag_init
        except:
            assert 0
        else:
            assert 1
            
    def test_initialization_from_cmd_args(self):
        from autoglacier.ag_command import _construst_argparse_parser
        parser = _construst_argparse_parser()
        # should prepare conf.json...
        args = parser.parse_args(['init', '--gen-keys', './conf.json'])
        args.func(args)
        # should clean...


