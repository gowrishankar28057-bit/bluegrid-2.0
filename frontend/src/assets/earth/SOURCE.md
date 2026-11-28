# Earth daymap source and usage

`daymap.jpg` is an unchanged NASA **Blue Marble: Next Generation** global base map for **July 2004**. It is a historical monthly satellite composite, not current weather, renewable resource data, or evidence of site feasibility.

| Property | Value |
| --- | --- |
| Dimensions | 5400 x 2700 pixels |
| Format | JPEG, RGB, global equirectangular color map |
| File size | 1,617,810 bytes |
| SHA-256 | `f55226d46d27e05511f2118dc6aa24f5dbf9b6b2cddc87cc6e0e7dd067c00b11` |
| Local changes | None; original download bytes retained |
| Retrieved | 28 November 2026 |

## Primary sources

- [NASA collection and production credits](https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/)
- [NASA base-map downloads](https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/) - July, global, 5400 x 2700 JPEG
- [Exact NASA image download](https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-base/july/world.200407.3x5400x2700.jpg)

## Credit and rights

**NASA Earth Observatory.** Blue Marble: Next Generation was produced by Reto Stockli, NASA Goddard Space Flight Center.

This NASA imagery remains separate from the application's MIT-licensed code. [NASA's media usage guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) state that NASA content, including texture maps, generally is not subject to copyright in the United States and may be used for educational and informational simulations and websites, subject to the guidelines. NASA's [Earth Science FAQ](https://science.nasa.gov/earth/faq/) also permits reuse of its materials, including commercial reuse, unless otherwise marked. The linked source identifies no separate copyright restriction for this map.

Retain the NASA source credit. No NASA endorsement, review, certification, or affiliation is implied. NASA identifiers and logos are not included in this texture.

## Rendering context

The map has north at the top, longitude -180 degrees at the left edge and +180 degrees at the right edge, and the equator at vertical center. Use it as an sRGB color texture. It is served locally by the frontend; the globe does not need to request NASA imagery at runtime.

The collection describes compositing limitations, including residual cloud/snow ambiguity and a uniform deep-ocean color. This map provides geographic visual context and does not define political borders or validated engineering coverage.
