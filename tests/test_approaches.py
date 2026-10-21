import importlib.util, json
from acehid import approaches
from acehid.common import ROOT

def _glossary(tmp_path):
    spec = importlib.util.spec_from_file_location("sc", ROOT / "space/core.py"); core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
    p = tmp_path / "g.csv"
    p.write_text("input,target,error_category,error_type,severity,source,wer,translate_ind,sentiment\n"
                 "zaaba,zaaba,none,none,none,x,0,\"rumah, tempat tinggal\",neutral\nzaaki,zaaki,none,none,none,x,0,pergi (jauh),neutral\n", encoding="utf-8")
    return core.Glossary.load(str(p)), core._fold

def test_direct_looks_words_up_and_keeps_unknown_words(tmp_path):
    t = approaches.Translator(_glossary(tmp_path))
    assert t.direct("Zaaba lon, qqq!") == "Rumah lon, qqq!"

def test_transfer_splits_prefix_and_suffix_and_maps_function_words(tmp_path):
    t = approaches.Translator(_glossary(tmp_path))
    assert t.transfer("Zaabajih hana jizaaki.") == "Rumahnya tidak dia pergi."
    assert t.transfer("Lon jizaaki") == "Saya pergi"                  # the subject is already written (lon): no extra pronoun
