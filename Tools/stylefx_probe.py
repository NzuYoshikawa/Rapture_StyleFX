# -*- coding: utf-8 -*-
# SF01 stage-0 probe (run via ue_remote against a live AOV_test editor).
# Dumps version-sensitive facts the brief says to verify before building the
# Post Process material: BlendableLocation enum names, SceneTextureId names,
# MaterialDomain names, Custom/SceneTexture expression properties, the
# MaterialEditingLibrary API surface, project maps, and PostProcessVolumes in
# the current level. Read-only. Writes a report next to this script.
# NOTE: ue_remote ExecuteFile misreads a literal dot-py token in the body, so
# none appears here.
import unreal
import os

LINES = []


def emit(s=""):
    LINES.append(str(s))


def section(title):
    emit("")
    emit("=" * 64)
    emit(title)
    emit("-" * 64)


def enum_dump(cls_name):
    try:
        cls = getattr(unreal, cls_name)
    except Exception as e:
        emit("  (no unreal.%s: %s)" % (cls_name, e))
        return
    for n in dir(cls):
        if n.startswith("_"):
            continue
        try:
            v = getattr(cls, n)
            emit("  %-44s = %r" % (n, int(v)))
        except Exception:
            emit("  %-44s = %r" % (n, getattr(cls, n)))


def props_dump(cls_name):
    try:
        obj = getattr(unreal, cls_name)()
    except Exception as e:
        emit("  (cannot instantiate unreal.%s: %s)" % (cls_name, e))
        return
    seen = set()
    for n in dir(obj):
        if n.startswith("_") or callable(getattr(type(obj), n, None)):
            continue
        if n in seen:
            continue
        seen.add(n)
        try:
            emit("  %-40s : %r" % (n, obj.get_editor_property(n)))
        except Exception:
            emit("  %-40s : <unreadable>" % n)


def main():
    section("ENGINE")
    try:
        emit("  version = " + unreal.SystemLibrary.get_engine_version())
    except Exception as e:
        emit("  version error: %s" % e)

    section("BlendableLocation (pick After-Tonemapping; brief 4.1)")
    enum_dump("BlendableLocation")

    section("MaterialDomain (need MD_POST_PROCESS equivalent)")
    enum_dump("MaterialDomain")

    section("SceneTextureId (need SceneDepth=1 and PostProcessInput0=14 names)")
    enum_dump("SceneTextureId")

    section("MaterialExpressionCustom editor properties")
    props_dump("MaterialExpressionCustom")

    section("MaterialExpressionSceneTexture editor properties")
    props_dump("MaterialExpressionSceneTexture")

    section("MaterialEditingLibrary API (connect / create / set / recompile)")
    try:
        names = [n for n in dir(unreal.MaterialEditingLibrary) if not n.startswith("_")]
        for n in names:
            low = n.lower()
            if any(k in low for k in ("connect", "create", "expression", "recompile",
                                      "set_material", "param", "property", "delete")):
                emit("  " + n)
    except Exception as e:
        emit("  error: %s" % e)

    section("Maps in /Game (verification level candidates: M0b / M0)")
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        wp = unreal.TopLevelAssetPath("/Script/Engine", "World")
        f = unreal.ARFilter(class_paths=[wp], recursive_paths=True,
                            package_paths=["/Game"])
        for a in ar.get_assets(f):
            emit("  " + str(a.package_name))
    except Exception as e:
        emit("  error: %s" % e)

    section("Current editor world + PostProcessVolumes")
    try:
        es = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = es.get_editor_world()
        emit("  world = %s" % (world.get_name() if world else None))
        acts = unreal.GameplayStatics.get_all_actors_of_class(world,
               unreal.PostProcessVolume)
        if not acts:
            emit("  (no PostProcessVolume in current level)")
        for a in acts:
            try:
                unbound = a.get_editor_property("unbound")
            except Exception:
                unbound = "?"
            emit("  %s  unbound=%s" % (a.get_actor_label(), unbound))
    except Exception as e:
        emit("  error: %s" % e)

    report = r"E:\UE5\AOV_test\Saved\StyleFX\probe_report.txt"
    print("\n".join(LINES))
    try:
        with open(report, "w", encoding="utf-8") as fh:
            fh.write("\n".join(LINES))
        print("\n[probe] wrote " + report)
    except Exception as e:
        print("\n[probe] report write failed: %s" % e)


main()
