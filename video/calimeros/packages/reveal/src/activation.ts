import { assertAttributes, assertEmptyElement, createMarkupSurfaceFacet, textAttribute } from "@hypit/hypit/markup";
import { canonicalize, sameType } from "@hypit/hypit/protocol";
import { sealGraphFragment } from "@hypit/hypit/author";
import { createAdmissionPackageFacet } from "@hypit/hypit/admission";
import { createProducerPackageFacet } from "@hypit/hypit/producer";
import type { ProducerPackage } from "@hypit/hypit/producer";
import type { AdmissionPackage } from "@hypit/hypit/admission";
import type { FragmentOperation } from "@hypit/hypit/author";
import type { ModuleManifest, TypeRef } from "@hypit/hypit/protocol";
import type { StructuredSurfaceHandler, SurfaceResolvedReference } from "@hypit/hypit/markup";
import { compositionTypes } from "@hypit/composition";
import { mediaTypes } from "@hypit/media";
import type { FontStackRef } from "@hypit/media";
import type { Timeline } from "@hypit/timeline";
import { timelineTypes } from "@hypit/timeline";
import { spatialTypes } from "@hypit/spatial";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalInstantFor, temporalTypes } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
import { resolveTemporalInstantReference, resolveTemporalWindowReference, resolveTemporalContext,
  temporalContextAttributeVocabulary, temporalInstantAttributeNames, temporalInstantAttributeVocabulary,
  temporalWindowAttributeNames, temporalWindowAttributeVocabulary } from "@hypit/temporal/markup";
import { beatKinds, renderReveal } from "./render.js";
import type { Beat, BeatKind, RevealOptions } from "./render.js";

const module = { name: "@calimeros/reveal", version: "1" } as const;
const types = Object.fromEntries(["Options", "Beat", "Beats"].map(name => [name, { module, name }])) as Record<"Options" | "Beat" | "Beats", TypeRef>;
const producers = Object.fromEntries(["empty", "append", "render"].map(name => [name, { module, name }])) as Record<"empty" | "append" | "render", { module: typeof module; name: string }>;

export const manifest: ModuleManifest = { format: "hypit.module@1", ...module,
  dependencies: [compositionTypes.visualTrack, mediaTypes.fontStack, timelineTypes.timeline, spatialTypes.frame, temporalTypes.instant].map(type => ({ module: type.module })),
  types: Object.values(types).map(type => ({ name: type.name })), capabilities: [], producers: [
    { name: "empty", inputs: [], outputs: [{ name: "beats", type: types.Beats }], needs: [] },
    { name: "append", inputs: [{ name: "beats", type: types.Beats }, { name: "beat", type: types.Beat },
      { name: "at", type: temporalTypes.instant }, { name: "timeline", type: timelineTypes.timeline }], outputs: [{ name: "beats", type: types.Beats }], needs: [] },
    { name: "render", inputs: [{ name: "beats", type: types.Beats }, { name: "options", type: types.Options },
      { name: "timeline", type: timelineTypes.timeline }, { name: "within", type: spatialTypes.frame },
      { name: "window", type: temporalTypes.window }, { name: "font", type: mediaTypes.fontStack },
      { name: "headline", type: mediaTypes.fontStack }], outputs: [{ name: "visual", type: compositionTypes.visualTrack }], needs: [] },
  ],
};

const inline = <T>(record: { value: { kind: string; value?: unknown } } | undefined): T => {
  if (record?.value.kind !== "inline") throw new Error("Reveal inputs must be inline values.");
  return record.value.value as T;
};
const value = (data: unknown) => ({ kind: "inline" as const, value: canonicalize(data) });

const component: ProducerPackage & AdmissionPackage = { producers: [
  { producer: producers.empty, handler: () => ({ outputs: { beats: value([]) }, needs: {} }) },
  { producer: producers.append, handler: ({ inputs }) => {
    const beat = inline<Omit<Beat, "at">>(inputs.beat), at = inline<TemporalInstant>(inputs.at);
    const beats = inline<Beat[]>(inputs.beats);
    assertTemporalInstantFor(at, { subjectId: beat.id, timeline: inline<Timeline>(inputs.timeline) });
    if (beats.some(item => item.id === beat.id) || (beats.at(-1)?.at.frame ?? -1) > at.frame) throw new Error("Reveal events need unique ids and strictly increasing times.");
    return { outputs: { beats: value([...beats, { ...beat, at }]) }, needs: {} };
  } },
  { producer: producers.render, handler: ({ inputs }) => ({ outputs: { visual: value(renderReveal(inline<Timeline>(inputs.timeline),
    inline<SpatialFrame>(inputs.within), inline<TemporalWindow>(inputs.window), inline<FontStackRef>(inputs.font),
    inline<FontStackRef>(inputs.headline), inline<Beat[]>(inputs.beats), inline<RevealOptions>(inputs.options))) }, needs: {} }) },
] };

export const decodeSurface: StructuredSurfaceHandler = ({ element, resolveReference }) => {
  assertAttributes(element, ["id", "timeline", "within", "font", "headline", "cta", ...temporalWindowAttributeNames]);
  const id = textAttribute(element, "id"), context = resolveTemporalContext({ element, resolveReference });
  const window = resolveTemporalWindowReference({ element, resolveReference });
  const reference = (name: string, type: TypeRef): SurfaceResolvedReference => {
    const raw = element.attributes[name];
    if (typeof raw !== "object" || raw.kind !== "reference") throw new Error(`${name} must be a reference.`);
    const found = resolveReference(raw.path);
    if (found === undefined || !sameType(found.type, type)) throw new Error(`${name} has the wrong Type.`);
    return found;
  };
  const options: RevealOptions = { id, cta: textAttribute(element, "cta") };
  const records = [{ id: `${id}.options`, type: types.Options, value: value(options), range: element.range }];
  const inputs = [{ name: "timeline", type: timelineTypes.timeline }, { name: "within", type: spatialTypes.frame },
    { name: "font", type: mediaTypes.fontStack }, { name: "headline", type: mediaTypes.fontStack },
    { name: "window", type: temporalTypes.window }, { name: "options", type: types.Options }];
  const bindings: Record<string, SurfaceResolvedReference["ref"]> = { timeline: context.timeline.ref, within: reference("within", spatialTypes.frame).ref,
    font: reference("font", mediaTypes.fontStack).ref, headline: reference("headline", mediaTypes.fontStack).ref,
    window: window.ref, options: { kind: "record", id: `${id}.options` } };
  const input = (name: string) => ({ kind: "fragment-input" as const, name });
  const operation = (name: string) => ({ kind: "fragment-operation" as const, operation: name });
  const operations: FragmentOperation[] = [{ id: "empty", producer: producers.empty, inputs: {}, result: { kind: "output", name: "beats" } }];
  let previous = "empty", index = 0;
  for (const child of element.children) {
    if (child.kind === "text") { if (child.value.trim()) throw new Error("Reveal accepts Beat children."); continue; }
    if (child.name.split(":").at(-1) !== "Beat") throw new Error("Reveal accepts Beat children.");
    assertAttributes(child, ["id", "kind", "text", "sub", ...temporalInstantAttributeNames]); assertEmptyElement(child);
    const kind = textAttribute(child, "kind") as BeatKind;
    if (!beatKinds.includes(kind)) throw new Error(`Beat kind must be one of ${beatKinds.join(", ")}.`);
    const sub = child.attributes.sub === undefined ? "" : textAttribute(child, "sub");
    const at = resolveTemporalInstantReference({ element: child, resolveReference });
    const key = `beat-${++index}`;
    records.push({ id: `${id}.${key}`, type: types.Beat, value: value({ id: textAttribute(child, "id"), kind, text: textAttribute(child, "text"), sub }), range: child.range });
    inputs.push({ name: key, type: types.Beat }, { name: `${key}-at`, type: temporalTypes.instant });
    bindings[key] = { kind: "record", id: `${id}.${key}` }; bindings[`${key}-at`] = at.ref;
    operations.push({ id: key, producer: producers.append, inputs: { beats: operation(previous), beat: input(key), at: input(`${key}-at`), timeline: input("timeline") }, result: { kind: "output", name: "beats" } });
    previous = key;
  }
  if (!index) throw new Error("Reveal requires a Beat.");
  operations.push({ id: "render", producer: producers.render, inputs: { beats: operation(previous), options: input("options"),
    timeline: input("timeline"), within: input("within"), font: input("font"), headline: input("headline"), window: input("window") }, result: { kind: "output", name: "visual" } });
  const fragment = sealGraphFragment({ inputs, operations, exports: [{ name: "visual", type: compositionTypes.visualTrack, root: operation("render") }] });
  return { records, fragments: [fragment], components:
    [{ id, fragment: fragment.id, inputs: bindings, outputs: { visual: `${id}.visual` }, range: element.range }], exports: [`${id}.visual`] };
};

const declaration = { name: "reveal", tag: "Reveal", mode: "structured" as const,
  outputs: [compositionTypes.visualTrack, ...Object.values(types)],
  vocabulary: { summary: "Minimal brand reel: a whole egg wobbles, cracks on its events, opens and reveals the logo with a tagline.", attributes: [
    ...temporalContextAttributeVocabulary, ...temporalWindowAttributeVocabulary,
    ...["id", "within", "font", "headline"].map(name => ({ name, kind: "expression" as const, required: true, summary: name })),
    { name: "cta", kind: "literal" as const, required: true, summary: "End-card call to action button." },
  ], children: [{ tag: "Beat", cardinality: "many" as const, summary: `One event at its Instant. kind: ${beatKinds.join(" | ")}.`, attributes: [
    ...["id", "kind", "text"].map(name => ({ name, kind: "literal" as const, required: true, summary: name })),
    { name: "sub", kind: "literal" as const, required: false, summary: "Secondary line." }, ...temporalInstantAttributeVocabulary,
  ] }], ports: [{ name: "visual", type: compositionTypes.visualTrack, summary: "The complete commercial picture." }],
    example: '<rv:Reveal id="reel" timeline={t.timeline} within={canvas.bounds} font={body} headline={head} during={t.window} cta="Kom proeven"><rv:Beat id="c1" kind="crack" text="" at={t.c1}/></rv:Reveal>',
  },
};

export const hypitPackage = { format: "hypit.package@1" as const, modules: [{ manifest }],
  facets: [createProducerPackageFacet(component), createAdmissionPackageFacet(component),
    createMarkupSurfaceFacet({ module, declaration, handler: decodeSurface })] };
export default hypitPackage;
