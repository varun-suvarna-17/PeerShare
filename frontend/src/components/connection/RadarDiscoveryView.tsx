import { Laptop } from 'lucide-react'
import { motion } from 'motion/react'
import type { DiscoveredDevice } from '../../types/api'

interface RadarDiscoveryViewProps {
  devices: DiscoveredDevice[]
  selectedDevice: DiscoveredDevice | null
  onSelect: (device: DiscoveredDevice) => void
  discovering?: boolean
  thisLaptopName?: string
}

export function RadarDiscoveryView({
  devices,
  selectedDevice,
  onSelect,
  discovering = false,
  thisLaptopName = 'This laptop',
}: RadarDiscoveryViewProps) {
  // Compute positions around concentric rings for discovered devices
  // Ring 1 (inner orbit): radius 130px, Ring 2 (outer orbit): radius 190px
  const devicePositions = devices.map((device, idx) => {
    const isEven = idx % 2 === 0
    const radius = isEven ? 140 : 190
    // Distribute angles across upper and side arcs so they don't overlap bottom text
    const angleOffset = isEven ? -40 + idx * 75 : 20 + idx * 75
    const angleRad = (angleOffset * Math.PI) / 180
    const x = Math.cos(angleRad) * radius
    const y = Math.sin(angleRad) * radius
    return { device, x, y }
  })

  return (
    <div className="relative flex flex-col items-center justify-center py-6 select-none overflow-hidden min-h-[380px] sm:min-h-[440px]">
      {/* Concentric Orbit Rings matching reference mockup */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {/* Ring 4 (outermost) */}
        <div className="w-[420px] h-[420px] rounded-full border border-[#e6b99d]/35" />
        {/* Ring 3 */}
        <div className="absolute w-[320px] h-[320px] rounded-full border border-[#e6b99d]/45" />
        {/* Ring 2 */}
        <div className="absolute w-[220px] h-[220px] rounded-full border border-[#e6b99d]/55" />
        {/* Ring 1 (innermost) */}
        <div className="absolute w-[130px] h-[130px] rounded-full border border-[#e6b99d]/60" />

        {/* Animated Radar Ripples */}
        {discovering && (
          <>
            <div className="absolute w-24 h-24 rounded-full border-2 border-[var(--primary)]/30 radar-ripple" />
            <div
              className="absolute w-24 h-24 rounded-full border-2 border-[var(--primary)]/20 radar-ripple"
              style={{ animationDelay: '1.2s' }}
            />
          </>
        )}
      </div>

      {/* Center Node: "This laptop" matching mockup */}
      <div className="relative z-10 flex flex-col items-center text-center">
        <motion.div
          animate={discovering ? { scale: [1, 1.04, 1] } : {}}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          className="w-18 h-18 sm:w-20 sm:h-20 rounded-full bg-[var(--primary)] text-white flex items-center justify-center shadow-md relative"
        >
          <div className="absolute inset-0 rounded-full border-2 border-white/20" />
          <Laptop className="w-8 h-8 stroke-[2.25]" />
        </motion.div>
        <span className="mt-2 text-xs font-semibold text-[var(--text)]">{thisLaptopName}</span>
      </div>

      {/* Discovered Orbiting Devices matching mockup */}
      {devicePositions.map(({ device, x, y }, i) => {
        const isSelected = selectedDevice?.device_id === device.device_id

        return (
          <motion.div
            key={device.device_id}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
            style={{
              transform: `translate(${x}px, ${y}px)`,
            }}
            onClick={() => onSelect(device)}
            className="absolute z-20 flex flex-col items-center text-center cursor-pointer group"
          >
            {/* Device Circle Icon */}
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              className={`w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center shadow-md transition-all duration-200 relative ${
                isSelected
                  ? 'bg-white ring-4 ring-[var(--primary)] shadow-lg'
                  : 'bg-[var(--bg-light)] border border-[#e6b99d] group-hover:border-[var(--primary)] group-hover:bg-white'
              }`}
            >
              <Laptop
                className={`w-7 h-7 ${
                  isSelected ? 'text-[var(--primary)]' : 'text-[#502010]'
                }`}
              />

              {/* Online Green Status Dot on top-right from mockup */}
              <span className="absolute top-0 right-0 w-3.5 h-3.5 rounded-full bg-emerald-600 border-2 border-white shadow-xs" />
            </motion.div>

            {/* Device Name Label */}
            <span
              className={`mt-1.5 text-xs font-bold max-w-[130px] truncate px-2 py-0.5 rounded-md transition-colors ${
                isSelected
                  ? 'bg-[var(--primary)] text-white shadow-xs'
                  : 'text-[var(--text)] group-hover:text-[var(--primary)]'
              }`}
            >
              {device.device_name}
            </span>
          </motion.div>
        )
      })}
    </div>
  )
}
