import { cn, getTechLogos } from '@/lib/utils'
import Image from 'next/image';
import React from 'react'

const DisplayTechIcons =  async ({ techStack }: TechIconProps) => {
    const techIcons = await getTechLogos(techStack);


    return (
        <div className="flex flex-row rounded-full">
          {techIcons.slice(0, 3).map(({ tech, url }, index) => (
            <div
              key={tech}
              className={cn("relative group bg-dark-300 p-2 flex items-center rounded-full justify-center", index >= 1 && "-ml-3")}
            >
              <span className="tech-tooltip">{tech}</span>
              <Image src={url} alt={tech} width={100} height={100} className="size-5 rounded-full"/>
            </div>
          ))}
        </div>
      );
}


export default DisplayTechIcons
