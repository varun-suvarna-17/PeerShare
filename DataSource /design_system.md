# Design System – PeerShare V2.0

## 1. Design Direction

PeerShare follows a modern, minimal, warm and friendly visual design.

The interface should feel:

- Clean and uncluttered.
- Friendly and approachable.
- Modern, with soft rounded elements.
- Easy to understand and navigate.
- Consistent across sender and receiver interfaces.
- Visually distinctive through typography and subtle styling.

The approved PeerShare dashboard mockup remains the primary visual reference.

However, the design should prioritize usability and HCI principles over unnecessary visual elements.

### Design Philosophy

- Human-Centered Design.
- Simplicity and minimalism.
- Consistent visual language.
- Clear visual hierarchy.
- Recognition over recall.
- Visibility of system status.
- Progressive disclosure.

Every UI element must serve a functional purpose.

---

## 2. Colour Palette

Use the following colour tokens consistently throughout the application.

IMPORTANT:
The main application background must now be pure white.

Preserve the existing warm OKLCH palette for accents, text and component styling.

```css
:root {
  /* Application backgrounds */
  --bg-dark: oklch(0.92 0.07 44);
  --bg: #FFFFFF;
  --bg-light: #FFFFFF;

  /* Typography */
  --text: oklch(0.15 0.14 44);
  --text-muted: oklch(0.4 0.14 44);

  /* Highlights */
  --highlight: oklch(1 0.14 44);

  /* Borders */
  --border: oklch(0.6 0.14 44);
  --border-muted: oklch(0.7 0.14 44);

  /* Brand colours */
  --primary: oklch(0.4 0.14 44);
  --secondary: oklch(0.4 0.14 224);

  /* Semantic colours */
  --danger: oklch(0.5 0.14 30);
  --warning: oklch(0.5 0.14 100);
  --success: oklch(0.5 0.14 160);
  --info: oklch(0.5 0.14 260);

  /* Additional neutral surface */
  --surface-muted: #F7F7F7;
}
```

### Colour Usage

| Token | Purpose |
|---|---|
| Background | Main application background – pure white |
| Background Dark | Sidebar and secondary surfaces |
| Background Light | Cards and elevated surfaces |
| Surface Muted | Drop zones and subtle secondary areas |
| Text | Primary headings and content |
| Text Muted | Supporting text and descriptions |
| Primary | Main buttons and important actions |
| Secondary | Secondary actions and highlights |
| Success | Successful transfers and online status |
| Danger | Failed transfers and errors |
| Warning | Pending operations and warnings |
| Info | Informational messages |

Do not introduce unrelated colours without a clear functional requirement.

---

## 3. Typography

Use a modern sans-serif typeface throughout the application.

### Typography Direction

Typography is an important part of PeerShare's visual identity.

Use italic styling thoughtfully to create a distinctive, friendly and modern appearance.

Recommended font:
- Inter
- Inter Italic

Alternatively, use another clean sans-serif family with proper italic variants.

### Typography Hierarchy

| Element | Size | Weight | Style |
|---|---|---|---|
| Page Heading | 28–32px | Semibold/Bold | Italic preferred |
| Section Heading | 18–22px | Semibold | Normal |
| Card Heading | 16–18px | Semibold | Normal |
| Body Text | 14–16px | Regular | Normal |
| Supporting Text | 12–14px | Regular | Normal |
| Labels | 12–14px | Medium | Normal |
| Brand Text | 28–36px | Bold | Italic |

### Italic Styling Guidelines

- Use italic styling for prominent page headings and selected brand elements.
- Supporting text should remain normally styled for readability.
- Do not italicize every text element.
- Maintain consistent typography across all screens.
- Avoid decorative or overly stylized fonts.

The overall result should feel elegant rather than excessively decorative.

---

## 4. Border Radius and Shapes

Rounded elements are a defining part of the PeerShare visual identity.

| Component | Border Radius |
|---|---|
| Primary Buttons | Fully rounded / pill |
| Secondary Buttons | Fully rounded / pill |
| Input Fields | 12–16px |
| Cards | 16–20px |
| Modals | 20px |
| Badges | Fully rounded |
| Navigation Items | 10–12px |
| Device Cards | 16–20px |

Avoid sharp corners and overly rectangular UI elements.

---

## 5. Buttons

### Primary Button

- Uses the primary colour.
- Fully rounded shape.
- Clear action-oriented label.
- Subtle hover transition.
- Visible disabled state.

### Secondary Button

- Uses a light background or outlined appearance.
- Fully rounded shape.
- Used for less important actions.

### Danger Button

- Uses the danger colour.
- Reserved for destructive or critical actions.

Buttons should have consistent height, padding and typography.

Avoid displaying multiple competing primary buttons on the same screen.

---

## 6. Cards and Containers

Cards should:

- Use white or subtle neutral backgrounds.
- Have rounded corners.
- Use subtle borders or shadows.
- Maintain consistent internal padding.
- Clearly separate related content.

IMPORTANT:

Do not place every section inside a card.

Avoid:
- Excessive cards.
- Nested cards.
- Repeated containers.
- Unnecessary decorative panels.
- Cards that simply duplicate information.

Use whitespace and dividers wherever they provide better visual organization.

---

## 7. Input Fields

Input fields should:

- Have rounded corners.
- Use consistent padding.
- Have clearly visible labels.
- Include focus and error states.
- Maintain sufficient contrast.

Apply consistent styling to text fields, search fields and numeric inputs.

---

## 8. Status Indicators

Use semantic colours consistently.

- Green: Connected, completed, successful.
- Red: Failed, disconnected, error.
- Yellow: Pending, waiting, warning.
- Blue: Information and active operations.

Status badges should use fully rounded shapes.

---

## 9. Layout and Spacing

Follow a consistent spacing scale:

- 4px – Very small gaps.
- 8px – Small gaps.
- 12px – Compact spacing.
- 16px – Standard spacing.
- 24px – Section spacing.
- 32px – Large spacing.
- 48px – Major layout separation.

Maintain sufficient whitespace between sections.

Avoid filling empty space with unnecessary components.

---

## 10. Application Layout

Follow the overall layout and visual hierarchy of the approved mockup.

The application may include:

- Sidebar navigation.
- Main content area.
- Dashboard overview.
- Device discovery and connection.
- File transfer interface.
- Transfer progress and visualization.
- Transfer history.
- Settings.

However, navigation and content must remain contextually relevant.

Do not force every section into every screen.

The sender and receiver interfaces should maintain the same visual language while displaying role-specific functionality.

---

## 11. HCI and UI Minimalism

Follow these mandatory principles:

1. One primary purpose per screen.
2. One clear primary action at a time.
3. Show information only when it is needed.
4. Avoid redundant buttons and navigation.
5. Provide immediate feedback for user actions.
6. Make system states visible.
7. Use progressive disclosure for advanced features.
8. Maintain consistency without making every screen look identical.

Do not add UI elements simply to make the interface look visually rich.

Every component must have a functional purpose.

---

## 12. Animations and Interactions

Use Motion for meaningful UI animations.

Subtle animations may be used for:

- Button hover and click states.
- Page transitions.
- Device connection states.
- File transfer progress.
- Packet transmission and ACK visualization.

Animations must communicate actual application events.

Do not use decorative animations that could be confused with real network activity.

---

## 13. Responsive Design

The interface should adapt to:

- Desktop screens.
- Laptop screens.
- Tablet screens.

Prioritize the desktop experience because the application is intended for laptop-to-laptop file transfers.

---

## 14. Implementation Guidelines

- Use the defined colour variables instead of hardcoding colours.
- Maintain reusable components.
- Keep spacing, typography and border radius consistent.
- Use sans-serif typography with selective italic styling.
- Avoid unnecessary gradients and decorative effects.
- Use Lucide React for icons.
- Use Motion for meaningful animations.
- Maintain consistent styling across all application pages.
- Follow this document as the single source of truth for UI styling.

---

## 15. Visual Reference

The approved PeerShare dashboard mockup remains the primary visual reference.

Preserve its:

- Warm accent palette.
- White application background.
- Rounded buttons and components.
- Soft card appearance.
- Minimal visual hierarchy.
- Friendly and modern aesthetic.
- Typography personality.

Do not independently introduce a completely different visual direction.

At the same time, do not copy the same layout across every screen.

Each screen should have a composition appropriate to its functionality.

---

## FINAL DESIGN GOAL

Build a premium, minimal, white-background desktop file-sharing application.

PeerShare should feel friendly, modern, elegant and effortless to use.

The combination of white backgrounds, warm accents, rounded elements and selective italic sans-serif typography should create a recognizable visual identity.

Usability always takes priority over decoration.