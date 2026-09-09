export const devConfig = {
  environmentName: "dev",
  region: "ap-northeast-1",
  vpcCidr: "10.10.0.0/16",
  publicSubnets: [
    {
      id: "PublicSubnet1",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.1.0/24",
    },
    {
      id: "PublicSubnet2",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.2.0/24",
    },
  ],
};
