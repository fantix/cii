CREATE MIGRATION m1sr6yrn3wxsp6t32ozrrjwgh2v6immmlbv66kfkecgwkf7ogt4gva
    ONTO initial
{
  CREATE TYPE default::Issue {
      CREATE LINK parent -> default::Issue;
      CREATE MULTI LINK refs -> default::Issue {
          CREATE PROPERTY reason -> std::str;
      };
  };
  CREATE TYPE default::Playbook {
      CREATE REQUIRED PROPERTY name -> std::str;
  };
  CREATE TYPE default::Run {
      CREATE REQUIRED LINK playbook -> default::Playbook;
  };
  CREATE TYPE default::Error {
      CREATE LINK issue -> default::Issue;
      CREATE REQUIRED LINK run -> default::Run;
  };
};
