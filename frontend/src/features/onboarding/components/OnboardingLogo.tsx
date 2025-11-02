const imgGroup = "http://localhost:3845/assets/14ec506f491e87722d5d1901c8c36aa9419f5fe5.svg";

export default function OnboardingLogo() {
  return (
    <div className="absolute left-8 top-8 z-10 rotate-90 pl-[20px]">
      <div className="h-[43px] w-[45px] relative">
        <img
          alt="Ultra Logo"
          className="block max-w-none size-full"
          src={imgGroup}
        />
      </div>
    </div>
  );
}
